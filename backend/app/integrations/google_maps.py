"""
Google Maps Platform Integration Adapter for Aarogya Sahayak.
Provides Places API (New), Geocoding API, and Routes API integrations with:
- Minimal field masks
- 10s timeout
- Transient error retry (429/5xx, max 2 attempts)
- Coordinate-rounded TTL caching
- Daily budget tracking
- Safe logging without PII or API credentials
"""

import time
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx
from app.config import settings

logger = logging.getLogger("google_maps_adapter")

# In-memory TTL cache: key -> (timestamp, data)
_CACHE: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes cache

# Daily request counter for budget tracking
_DAILY_REQUESTS = {
    "date": "",
    "count": 0
}

class GoogleMapsAdapterException(Exception):
    """Base exception for Google Maps API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

class GoogleMapsAuthException(GoogleMapsAdapterException):
    """Raised when API key is unauthorized or forbidden."""
    pass

class GoogleMapsQuotaException(GoogleMapsAdapterException):
    """Raised when quota or rate limit is reached."""
    pass

class GoogleMapsTimeoutException(GoogleMapsAdapterException):
    """Raised when Google API request times out."""
    pass


class GoogleMapsAdapter:
    """
    Adapter for Google Cloud Maps Platform APIs.
    """
    PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
    PLACES_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

    # Only requested necessary fields - NEVER use '*'
    FIELD_MASK = (
        "places.id,"
        "places.displayName,"
        "places.formattedAddress,"
        "places.location,"
        "places.primaryType,"
        "places.types,"
        "places.businessStatus,"
        "places.nationalPhoneNumber,"
        "places.googleMapsUri"
    )

    def __init__(self, server_key: Optional[str] = None, mode: Optional[str] = None):
        self.server_key = server_key or settings.GOOGLE_MAPS_SERVER_KEY
        self.mode = mode or getattr(settings, "GOOGLE_MAPS_MODE", "auto")
        self.daily_limit = getattr(settings, "GOOGLE_PLACES_DAILY_LIMIT", 500)

    @property
    def is_live(self) -> bool:
        if self.mode == "mock":
            return False
        if self.mode == "live":
            return bool(self.server_key)
        # auto mode
        return bool(self.server_key and len(self.server_key.strip()) > 5)

    def _check_budget(self) -> bool:
        today_str = time.strftime("%Y-%m-%d")
        if _DAILY_REQUESTS["date"] != today_str:
            _DAILY_REQUESTS["date"] = today_str
            _DAILY_REQUESTS["count"] = 0
        if _DAILY_REQUESTS["count"] >= self.daily_limit:
            logger.warning(f"Google Maps daily request budget reached ({self.daily_limit}).")
            return False
        _DAILY_REQUESTS["count"] += 1
        return True

    def _get_cache(self, key: str) -> Optional[Any]:
        if key in _CACHE:
            ts, val = _CACHE[key]
            if time.time() - ts < _CACHE_TTL_SECONDS:
                return val
            else:
                del _CACHE[key]
        return None

    def _set_cache(self, key: str, val: Any):
        _CACHE[key] = (time.time(), val)

    def _make_places_request(self, url: str, payload: Dict[str, Any], attempt: int = 1) -> Dict[str, Any]:
        """
        Executes POST request to Google Places API (New) with field mask and exponential backoff retry.
        """
        if not self.server_key:
            raise GoogleMapsAuthException("Google Maps Server Key is missing or invalid", status_code=401)

        if not self._check_budget():
            raise GoogleMapsQuotaException("Daily Google Places request limit reached", status_code=429)

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.server_key,
            "X-Goog-FieldMask": self.FIELD_MASK
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [401, 403]:
                    logger.error(f"Google Places API Auth Error: status={response.status_code}")
                    raise GoogleMapsAuthException(
                        "Map service configuration is not authorized or quota exceeded.",
                        status_code=response.status_code
                    )
                elif response.status_code in [429, 500, 502, 503, 504]:
                    if attempt <= 2:
                        logger.warning(f"Transient Google API error {response.status_code}, retrying attempt {attempt + 1}...")
                        time.sleep(0.5 * attempt)
                        return self._make_places_request(url, payload, attempt=attempt + 1)
                    raise GoogleMapsQuotaException(
                        "Search limit reached or service temporarily unavailable. Please try again shortly.",
                        status_code=response.status_code
                    )
                else:
                    logger.error(f"Google Places API unexpected status {response.status_code}: {response.text[:200]}")
                    raise GoogleMapsAdapterException(
                        f"Google Places API returned status {response.status_code}",
                        status_code=response.status_code
                    )
        except httpx.TimeoutException:
            if attempt <= 2:
                logger.warning(f"Google API timeout, retrying attempt {attempt + 1}...")
                time.sleep(0.5 * attempt)
                return self._make_places_request(url, payload, attempt=attempt + 1)
            raise GoogleMapsTimeoutException("Search took too long. Try again.", status_code=504)
        except (GoogleMapsAdapterException, GoogleMapsAuthException, GoogleMapsQuotaException, GoogleMapsTimeoutException):
            raise
        except Exception as e:
            logger.error(f"Google Places network error: {type(e).__name__}")
            raise GoogleMapsAdapterException(f"Network error communicating with Google Places: {str(e)}")

    LEGACY_PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    LEGACY_PLACES_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    def _make_legacy_places_request(self, url: str, params: Dict[str, Any], attempt: int = 1) -> List[Dict[str, Any]]:
        """
        Executes GET request to Google Places API (Legacy Web Services) and transforms to canonical shape.
        """
        if not self.server_key:
            raise GoogleMapsAuthException("Google Maps Server Key is missing or invalid", status_code=401)

        if not self._check_budget():
            raise GoogleMapsQuotaException("Daily Google Places request limit reached", status_code=429)

        params_with_key = {**params, "key": self.server_key}

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params_with_key)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    if status in ["OK", "ZERO_RESULTS"]:
                        raw_results = data.get("results", [])
                        canonical_places = []
                        for r in raw_results:
                            loc = r.get("geometry", {}).get("location", {})
                            place_id = r.get("place_id") or ""
                            canonical_places.append({
                                "id": f"places/{place_id}" if place_id else "",
                                "displayName": {"text": r.get("name", "")},
                                "formattedAddress": r.get("vicinity") or r.get("formatted_address") or "",
                                "location": {
                                    "latitude": loc.get("lat"),
                                    "longitude": loc.get("lng")
                                },
                                "primaryType": r.get("types", ["hospital"])[0] if r.get("types") else "hospital",
                                "types": r.get("types", []),
                                "businessStatus": r.get("business_status", "OPERATIONAL"),
                                "nationalPhoneNumber": None,
                                "googleMapsUri": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None
                            })
                        return canonical_places
                    elif status in ["REQUEST_DENIED", "OVER_QUERY_LIMIT"]:
                        logger.error(f"Google Legacy Places API error status={status}: {data.get('error_message')}")
                        raise GoogleMapsAuthException(
                            f"Google Places service error: {status} - {data.get('error_message')}",
                            status_code=403
                        )
                    else:
                        return []
                elif response.status_code in [401, 403]:
                    raise GoogleMapsAuthException("Map service configuration is not authorized or quota exceeded.", status_code=response.status_code)
                elif response.status_code in [429, 500, 502, 503, 504]:
                    if attempt <= 2:
                        time.sleep(0.5 * attempt)
                        return self._make_legacy_places_request(url, params, attempt=attempt + 1)
                    raise GoogleMapsQuotaException("Search limit reached or service temporarily unavailable.", status_code=response.status_code)
                else:
                    raise GoogleMapsAdapterException(f"Google Places legacy API status {response.status_code}")
        except (GoogleMapsAdapterException, GoogleMapsAuthException, GoogleMapsQuotaException):
            raise
        except Exception as e:
            logger.error(f"Google Places legacy request failed: {e}")
            raise GoogleMapsAdapterException(f"Network error in legacy places: {e}")

    def search_nearby(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 10000,
        included_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search nearby places using Google Places API (New), with automatic fallback to Legacy Places Web Services.
        """
        if not self.is_live:
            return self._mock_nearby_search(lat, lon, included_types)

        # Cache key rounded to ~300m
        rounded_lat = round(lat, 2)
        rounded_lon = round(lon, 2)
        cache_key = f"nearby:{rounded_lat}:{rounded_lon}:{radius_meters}:{','.join(sorted(included_types or []))}:{max_results}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Attempt 1: Places API (New)
        try:
            payload: Dict[str, Any] = {
                "maxResultCount": min(max_results, 20),
                "locationRestriction": {
                    "circle": {
                        "center": {
                            "latitude": lat,
                            "longitude": lon
                        },
                        "radius": float(min(radius_meters, 50000))
                    }
                }
            }
            if included_types:
                payload["includedTypes"] = included_types

            data = self._make_places_request(self.PLACES_NEARBY_URL, payload)
            places = data.get("places", [])
            self._set_cache(cache_key, places)
            return places
        except GoogleMapsAuthException as e:
            # If Places API (New) is not enabled on this key, fallback to Legacy Places Web Service
            logger.warning(f"Places API (New) returned auth error ({e}), trying Legacy Places Nearby Search...")
            try:
                legacy_params = {
                    "location": f"{lat},{lon}",
                    "radius": min(radius_meters, 50000),
                    "type": included_types[0] if included_types else "hospital"
                }
                places = self._make_legacy_places_request(self.LEGACY_PLACES_NEARBY_URL, legacy_params)
                self._set_cache(cache_key, places)
                return places
            except Exception as legacy_err:
                logger.error(f"Legacy Places Nearby Search also failed: {legacy_err}")
                raise

    def search_by_text(
        self,
        text_query: str,
        lat: float,
        lon: float,
        radius_meters: int = 10000,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Capability-specific text search using Google Places API (New) with Legacy Text Search fallback.
        """
        if not self.is_live:
            return self._mock_text_search(text_query, lat, lon)

        rounded_lat = round(lat, 2)
        rounded_lon = round(lon, 2)
        cache_key = f"text:{text_query}:{rounded_lat}:{rounded_lon}:{radius_meters}:{max_results}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Attempt 1: Places API (New) Text Search
        try:
            payload: Dict[str, Any] = {
                "textQuery": text_query,
                "maxResultCount": min(max_results, 20),
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": lat,
                            "longitude": lon
                        },
                        "radius": float(min(radius_meters, 50000))
                    }
                }
            }

            data = self._make_places_request(self.PLACES_TEXT_URL, payload)
            places = data.get("places", [])
            self._set_cache(cache_key, places)
            return places
        except Exception as e:
            logger.warning(f"Places API (New) Text Search error ({e}), trying Legacy Places Text Search...")
            try:
                legacy_params = {
                    "query": text_query,
                    "location": f"{lat},{lon}",
                    "radius": min(radius_meters, 50000)
                }
                places = self._make_legacy_places_request(self.LEGACY_PLACES_TEXT_URL, legacy_params)
                self._set_cache(cache_key, places)
                return places
            except Exception as legacy_err:
                logger.error(f"Legacy Places Text Search also failed: {legacy_err}")
                raise

    def geocode_manual_location(self, address_or_pin: str) -> List[Dict[str, Any]]:
        """
        Geocode a manual village name, locality, or 6-digit PIN code using Geocoding API.
        """
        if not self.is_live:
            return self._mock_geocoding(address_or_pin)

        cache_key = f"geocode:{address_or_pin.strip().lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        if not self.server_key:
            raise GoogleMapsAuthException("Google Maps Server Key is missing", status_code=401)

        params = {
            "address": address_or_pin,
            "components": "country:IN",
            "key": self.server_key
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(self.GEOCODING_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    if status in ["OK", "ZERO_RESULTS"]:
                        results = data.get("results", [])
                        self._set_cache(cache_key, results)
                        return results
                    elif status in ["REQUEST_DENIED", "OVER_QUERY_LIMIT"]:
                        raise GoogleMapsAuthException(f"Geocoding API error: {status}", status_code=403)
                    else:
                        return []
                else:
                    raise GoogleMapsAdapterException(f"Geocoding API HTTP {resp.status_code}", status_code=resp.status_code)
        except (GoogleMapsAdapterException, GoogleMapsAuthException, GoogleMapsQuotaException):
            raise
        except httpx.TimeoutException:
            raise GoogleMapsTimeoutException("Geocoding lookup timed out", status_code=504)
        except Exception as e:
            logger.error(f"Geocoding network exception: {type(e).__name__}")
            raise GoogleMapsAdapterException(f"Geocoding error: {str(e)}")

    def reverse_geocode_coordinates(self, lat: float, lng: float, language: Optional[str] = "en") -> Optional[Dict[str, Any]]:

        """
        Reverse geocodes real GPS coordinates via Google Maps Geocoding API.
        Returns standardized address components.
        """
        if not self.is_live:
            return self._mock_reverse_geocoding(lat, lng)

        cache_key = f"reverse_geo:{round(lat, 4)}:{round(lng, 4)}:{language}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        if not self.server_key:
            raise GoogleMapsAuthException("Google Maps Server Key is missing", status_code=401)

        lang_param = "mr" if language and "mr" in language.lower() else ("hi" if language and "hi" in language.lower() else "en")
        params = {
            "latlng": f"{lat},{lng}",
            "key": self.server_key,
            "language": lang_param
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(self.GEOCODING_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    if status in ["OK", "ZERO_RESULTS"]:
                        results = data.get("results", [])
                        if not results:
                            return None
                        first = results[0]
                        formatted_address = first.get("formatted_address", "")
                        place_id = first.get("place_id")
                        
                        village = None
                        locality = None
                        pincode = None
                        block = None
                        district = None
                        state = None

                        for comp in first.get("address_components", []):
                            types = comp.get("types", [])
                            if "locality" in types or "sublocality" in types:
                                if not village:
                                    village = comp.get("long_name")
                                locality = comp.get("long_name")
                            elif "postal_code" in types:
                                pincode = comp.get("long_name")
                            elif "administrative_area_level_3" in types or "sublocality_level_1" in types:
                                block = comp.get("long_name")
                            elif "administrative_area_level_2" in types:
                                district = comp.get("long_name")
                            elif "administrative_area_level_1" in types:
                                state = comp.get("long_name")

                        res = {
                            "formatted_address": formatted_address,
                            "village": village,
                            "locality": locality or village,
                            "pincode": pincode,
                            "postal_code": pincode,
                            "block": block,
                            "district": district,
                            "state": state or "Maharashtra",
                            "latitude": lat,
                            "longitude": lng,
                            "place_id": place_id,
                            "provider": "GOOGLE"
                        }
                        self._set_cache(cache_key, res)
                        return res
                    elif status in ["REQUEST_DENIED", "OVER_QUERY_LIMIT"]:
                        raise GoogleMapsAuthException(f"Geocoding API error: {status}", status_code=403)
                    else:
                        return None
                else:
                    raise GoogleMapsAdapterException(f"Geocoding API HTTP {resp.status_code}", status_code=resp.status_code)
        except (GoogleMapsAdapterException, GoogleMapsAuthException, GoogleMapsQuotaException):
            raise
        except httpx.TimeoutException:
            raise GoogleMapsTimeoutException("Reverse geocoding timed out", status_code=504)
        except Exception as e:
            logger.error(f"Reverse geocoding network exception: {e}")
            raise GoogleMapsAdapterException(f"Reverse geocoding error: {str(e)}")

    def _mock_reverse_geocoding(self, lat: float, lng: float) -> Dict[str, Any]:
        return {
            "formatted_address": f"GPS Location ({lat:.4f}, {lng:.4f}), Maharashtra, India",
            "village": None,
            "pincode": None,
            "block": None,
            "district": None,
            "state": "Maharashtra",
            "latitude": lat,
            "longitude": lng,
            "place_id": None
        }

    def compute_routes(

        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float
    ) -> Optional[Dict[str, Any]]:
        """
        Optional compute route distance and duration using Routes API (top results only).
        """
        if not self.is_live or not self.server_key:
            return None

        cache_key = f"route:{round(origin_lat,3)}:{round(origin_lng,3)}->{round(dest_lat,3)}:{round(dest_lng,3)}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.server_key,
            "X-Goog-FieldMask": "routes.distanceMeters,routes.duration"
        }
        payload = {
            "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
            "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
            "travelMode": "DRIVE"
        }

        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(self.ROUTES_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    routes = resp.json().get("routes", [])
                    if routes:
                        dist_m = routes[0].get("distanceMeters", 0)
                        dur_str = routes[0].get("duration", "0s")
                        # parse duration like "300s"
                        dur_sec = int(dur_str.rstrip("s")) if dur_str.endswith("s") else 0
                        res = {
                            "distance_km": round(dist_m / 1000.0, 1),
                            "travel_minutes": math.ceil(dur_sec / 60.0)
                        }
                        self._set_cache(cache_key, res)
                        return res
        except Exception as e:
            logger.debug(f"Routes API non-critical fallback: {e}")
        return None

    # --- MOCK FALLBACK IMPLEMENTATIONS ---
    def _mock_nearby_search(self, lat: float, lon: float, included_types: Optional[List[str]]) -> List[Dict[str, Any]]:
        types = included_types or ["hospital"]
        if "pharmacy" in types:
            return [
                {
                    "id": "places/ChIJmock_pharmacy_01",
                    "displayName": {"text": "Jan Aushadhi Medical Kendra Kalyanpur", "languageCode": "en"},
                    "formattedAddress": "Main Bazaar Road, Near Bus Stand, Kalyanpur, Maharashtra 415001",
                    "location": {"latitude": lat + 0.005, "longitude": lon + 0.004},
                    "primaryType": "pharmacy",
                    "types": ["pharmacy", "drugstore", "health"],
                    "businessStatus": "OPERATIONAL",
                    "nationalPhoneNumber": "+91 2162 254101",
                    "googleMapsUri": f"https://maps.google.com/?cid=mock_pharmacy_01"
                }
            ]
        elif "medical_lab" in types:
            return [
                {
                    "id": "places/ChIJmock_lab_01",
                    "displayName": {"text": "Kalyanpur Clinical Pathology & Diagnostic Lab", "languageCode": "en"},
                    "formattedAddress": "Station Road, Opposite Govt Hospital, Kalyanpur 415001",
                    "location": {"latitude": lat + 0.006, "longitude": lon - 0.003},
                    "primaryType": "medical_lab",
                    "types": ["medical_lab", "health"],
                    "businessStatus": "OPERATIONAL",
                    "nationalPhoneNumber": "+91 2162 254102",
                    "googleMapsUri": f"https://maps.google.com/?cid=mock_lab_01"
                }
            ]
        else:
            return [
                {
                    "id": "places/ChIJmock_hosp_01",
                    "displayName": {"text": "Kalyanpur Community Hospital & Trauma Centre", "languageCode": "en"},
                    "formattedAddress": "NH-4 Bypass Road, Kalyanpur, Maharashtra 415001",
                    "location": {"latitude": lat + 0.008, "longitude": lon + 0.005},
                    "primaryType": "hospital",
                    "types": ["hospital", "health", "doctor"],
                    "businessStatus": "OPERATIONAL",
                    "nationalPhoneNumber": "+91 2162 254000",
                    "googleMapsUri": f"https://maps.google.com/?cid=mock_hosp_01"
                },
                {
                    "id": "places/ChIJmock_hosp_02",
                    "displayName": {"text": "Sanjeevani Maternity & General Nursing Home", "languageCode": "en"},
                    "formattedAddress": "Shivaji Chowk, Kalyanpur, Maharashtra 415001",
                    "location": {"latitude": lat - 0.009, "longitude": lon + 0.007},
                    "primaryType": "hospital",
                    "types": ["hospital", "health"],
                    "businessStatus": "OPERATIONAL",
                    "nationalPhoneNumber": "+91 2162 254050",
                    "googleMapsUri": f"https://maps.google.com/?cid=mock_hosp_02"
                }
            ]

    def _mock_text_search(self, text_query: str, lat: float, lon: float) -> List[Dict[str, Any]]:
        q_lower = text_query.lower()
        if "tb" in q_lower or "dots" in q_lower:
            name = "District TB Diagnostic & Nikshay Treatment Centre"
            p_type = "hospital"
        elif "maternity" in q_lower or "delivery" in q_lower:
            name = "Matruchhaya Maternity & Child Hospital"
            p_type = "hospital"
        elif "diabetes" in q_lower or "blood pressure" in q_lower or "ncd" in q_lower:
            name = "LifeCare NCD & Diabetes Care Clinic"
            p_type = "doctor"
        elif "ayushman" in q_lower or "scheme" in q_lower:
            name = "Ayushman Bharat Help Desk & Citizen CSC Centre"
            p_type = "local_government_office"
        elif "surgery" in q_lower or "surgical" in q_lower:
            name = "Sub-District Surgical Hospital & Operation Theatre"
            p_type = "hospital"
        elif "children" in q_lower or "vaccination" in q_lower:
            name = "Vatsalya Pediatric & Universal Vaccination Centre"
            p_type = "hospital"
        else:
            name = f"General Health Centre ({text_query.split()[0].title()})"
            p_type = "hospital"

        return [
            {
                "id": f"places/ChIJmock_text_{abs(hash(text_query)) % 100000}",
                "displayName": {"text": name, "languageCode": "en"},
                "formattedAddress": f"Main Road, Kalyanpur Block, Maharashtra 415001",
                "location": {"latitude": lat + 0.012, "longitude": lon - 0.008},
                "primaryType": p_type,
                "types": [p_type, "health"],
                "businessStatus": "OPERATIONAL",
                "nationalPhoneNumber": "+91 2162 254999",
                "googleMapsUri": "https://maps.google.com/?cid=mock_text_search"
            }
        ]

    def _mock_geocoding(self, query: str) -> List[Dict[str, Any]]:
        clean_q = query.strip()
        return [
            {
                "formatted_address": f"{clean_q}, Maharashtra, India",
                "geometry": {
                    "location": {"lat": 18.5204, "lng": 73.8567},
                    "location_type": "APPROXIMATE"
                },
                "place_id": f"ChIJmock_geo_{clean_q}",
                "address_components": [
                    {"long_name": clean_q, "short_name": clean_q, "types": ["locality", "political"]},
                    {"long_name": "District 04", "short_name": "D04", "types": ["administrative_area_level_2", "political"]},
                    {"long_name": "Maharashtra", "short_name": "MH", "types": ["administrative_area_level_1", "political"]},
                    {"long_name": "India", "short_name": "IN", "types": ["country", "political"]},
                    {"long_name": "415001", "short_name": "415001", "types": ["postal_code"]}
                ]
            }
        ]

google_maps_adapter = GoogleMapsAdapter()
