import React, { useState, useEffect, useRef } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  ArrowLeft, MapPin, Navigation, Phone, Clock, AlertTriangle, ShieldCheck,
  Search, Mic, Volume2, User, Activity, Baby, Stethoscope, HeartPulse,
  Syringe, FlaskConical, Pill, CheckCircle2, ChevronRight, Share2, Copy,
  Calendar, Building2, ExternalLink, RefreshCw, Eye, Sparkles, X, Info,
  Compass, Radio, Map
} from "lucide-react";
import { apiClient, FacilitySearchForm, FacilityServiceCode, FacilityLocationState, FacilitySearchResultItem } from "@aarogya/api-client";
import { LocationService, LocationData, LocationReactiveState } from "@aarogya/location";
import { GoogleMapView } from "./GoogleMapView";

interface FacilitiesScreenProps {
  onBack?: () => void;
  initialService?: FacilityServiceCode;
  initialUrgency?: string;
  initialSearchId?: string;
}

export const FacilitiesScreen: React.FC<FacilitiesScreenProps> = ({
  onBack,
  initialService,
  initialUrgency,
  initialSearchId
}) => {
  const { t, locale } = useLanguage();
  const currentLang = locale || "mr-IN";

  // Setup reverse geocode provider for LocationService
  useEffect(() => {
    LocationService.setReverseGeocodeProvider(async (lat: number, lng: number) => {
      try {
        const res = await apiClient.reverseGeocodeLocation(lat, lng, currentLang);
        return res?.data || res;
      } catch (err) {
        console.warn("Reverse geocode provider failed:", err);
        return null;
      }
    });
  }, [currentLang]);


  // 10 Stable Healthcare-Category Cards with verified capabilities & localized explanations
  // 10 Stable Healthcare-Category Cards with verified capabilities & localized explanations
  const CATEGORIES = [
    {
      code: "EMERGENCY_CARE" as FacilityServiceCode,
      icon: Activity,
      bg: "#FEE2E2",
      color: "#991B1B",
      titleMr: "आपत्कालीन व अपघात (२४x७)",
      titleHi: "आपातकालीन देखभाल (24x7)",
      titleEn: "Emergency Care",
      descMr: "तातडीचे उपचार, अपघात, छातीत दुखणे, श्वास घेण्यास त्रास, गंभीर जखमा व २४ तास डॉक्टर सुविधा",
      descHi: "गंभीर आपातकाल, सीने में दर्द, दुर्घटना, और 24x7 डॉक्टर व ट्रॉमा सुविधा",
      descEn: "24x7 emergency stabilization, casualty, trauma, chest pain, and critical care",
      isEmergency: true
    },
    {
      code: "GENERAL_DOCTOR_PHC" as FacilityServiceCode,
      icon: Stethoscope,
      bg: "#EFF6FF",
      color: "#1E40AF",
      titleMr: "डॉक्टर / प्राथमिक आरोग्य केंद्र (OPD)",
      titleHi: "सामान्य डॉक्टर / प्राथमिक स्वास्थ्य केंद्र",
      titleEn: "General Doctor / PHC",
      descMr: "ताप, खोकला, अंगदुखी, प्राथमिक तपासणी आणि वैद्यकीय सल्लागार",
      descHi: "बुखार, सर्दी, खांसी और सामान्य चिकित्सीय परामर्श",
      descEn: "Outpatient primary screening, fever, common ailments, and medical officer consults"
    },
    {
      code: "PREGNANCY_DELIVERY" as FacilityServiceCode,
      icon: HeartPulse,
      bg: "#FCE7F3",
      color: "#9D174D",
      titleMr: "गरोदरपण व प्रसूती सेवा",
      titleHi: "गर्भावस्था एवं प्रसव सेवा",
      titleEn: "Pregnancy & Delivery",
      descMr: "गरोदर महिला तपासणी (ANC), सुरक्षित प्रसूती कक्ष, नवजात शिशू कक्ष व सिझेरियन सुविधा",
      descHi: "ANC जांच, सुरक्षित प्रसव, लेबर रूम और आपातकालीन प्रसूति सेवाएं",
      descEn: "Antenatal care (ANC), 24x7 labor room, institutional delivery, and obstetric care"
    },
    {
      code: "CHILD_HEALTH_VACCINATION" as FacilityServiceCode,
      icon: Baby,
      bg: "#FEF3C7",
      color: "#92400E",
      titleMr: "बाल आरोग्य व नियमित लसीकरण",
      titleHi: "शिशु स्वास्थ्य व नियमित टीकाकरण",
      titleEn: "Child Health & Vaccination",
      descMr: "० ते ५ वयोगटातील मुलांचे लसीकरण, वजन तपासणी, कुपोषण उपचार व बालरोग तज्ज्ञ",
      descHi: "नियमित टीकाकरण, बाल स्वास्थ्य जांच व पोषण देखभाल",
      descEn: "Universal child immunization, pediatric checkups, RBSK, and nutrition center"
    },
    {
      code: "TESTS_DIAGNOSTICS" as FacilityServiceCode,
      icon: FlaskConical,
      bg: "#F3E8FF",
      color: "#6B21A8",
      titleMr: "रक्त चाचण्या व एक्स-रे (Diagnostics)",
      titleHi: "लैब टेस्ट एवं डिजिटल एक्स-रे",
      titleEn: "Tests & Diagnostics",
      descMr: "रक्त तपासणी, सीबीसी, लघवी तपासणी, डिजिटल एक्स-रे व सोनोग्राफी केंद्र",
      descHi: "ब्लड टेस्ट, सीबीसी, पेशाब जांच, डिजिटल एक्स-रे व अल्ट्रासाउंड",
      descEn: "Clinical laboratory, specimen collection, pathology, and digital X-ray diagnostics"
    },
    {
      code: "MEDICINES_PHARMACY" as FacilityServiceCode,
      icon: Pill,
      bg: "#ECFDF5",
      color: "#065F46",
      titleMr: "औषधालय (जन औषधी / सरकारी फार्मसी)",
      titleHi: "दवाखाना / जन औषधि केंद्र",
      titleEn: "Medicines & Pharmacy",
      descMr: "मोफत शासकीय औषधे, जन औषधी केंद्र व आवश्यक औषध पुरवठा",
      descHi: "सरकारी दवा वितरण, जन औषधि केंद्र और रियायती दवाएं",
      descEn: "Government pharmacy dispensary, PM Jan Aushadhi Kendra, and essential medicines"
    },
    {
      code: "TB_SERVICES" as FacilityServiceCode,
      icon: Activity,
      bg: "#FEF2F2",
      color: "#B91C1C",
      titleMr: "निक्षय टीबी उपचार केंद्र (TB DOTS)",
      titleHi: "निक्षय टीबी जांच एवं डॉट्स केंद्र",
      titleEn: "TB Services",
      descMr: "थुंकी तपासणी, मोफत टीबी औषधे, निक्षय पोषण योजना व श्वसन विकार",
      descHi: "बलगम जांच, टीबी का मुफ्त इलाज व निक्षय पोषण योजना",
      descEn: "NTEP designated microscopy, sputum testing, free DOTS regimen, and Nikshay desk"
    },
    {
      code: "DIABETES_BP_SERVICES" as FacilityServiceCode,
      icon: HeartPulse,
      bg: "#F0FDF4",
      color: "#166534",
      titleMr: "मधुमेह व बीपी तपासणी (NCD Clinic)",
      titleHi: "शुगर एवं बीपी जांच व परामर्श",
      titleEn: "Diabetes & BP Services",
      descMr: "रक्तदाब मोजणी, मधुमेह साखर तपासणी व दीर्घकालीन आजारांचे व्यवस्थापन",
      descHi: "ब्लड प्रेशर, शुगर जांच व नियमित गैर-संचारी रोग क्लिनिक",
      descEn: "Hypertension screening, blood glucose monitoring, and non-communicable disease care"
    },
    {
      code: "GOVERNMENT_SCHEME_DESK" as FacilityServiceCode,
      icon: Building2,
      bg: "#E0F2FE",
      color: "#0369A1",
      titleMr: "सरकारी योजना व आयुष्मान मदत कक्ष",
      titleHi: "आयुष्मान भारत व सरकारी योजना हेल्प डेस्क",
      titleEn: "Government Scheme Desk",
      descMr: "आयुष्मान कार्ड e-KYC, डाऊनलोड, जननी सुरक्षा योजना नोंदणी व CSC मदत",
      descHi: "आयुष्मान कार्ड e-KYC, पीएम-जय व सरकारी स्वास्थ्य योजना डेस्क",
      descEn: "Ayushman Bharat PM-JAY desk, e-KYC, JSY registration, and CSC government scheme portal"
    },
    {
      code: "DISTRICT_HOSPITAL_SURGERY" as FacilityServiceCode,
      icon: Building2,
      bg: "#F1F5F9",
      color: "#334155",
      titleMr: "जिल्हा रुग्णालय / शस्त्रक्रिया (Surgery)",
      titleHi: "जिला अस्पताल / ऑपरेशन एवं सर्जरी",
      titleEn: "District Hospital / Surgery",
      descMr: "मोठ्या शस्त्रक्रिया, ऑपरेशन थिएटर, आयसीयू (ICU), रक्तपेढी व तज्ज्ञ डॉक्टर",
      descHi: "मेजर सर्जरी, ऑपरेशन थिएटर, आईसीयू व स्पेशलिस्ट डॉक्टर सुविधा",
      descEn: "District hospital, general surgery, operation theater, ICU, and blood bank"
    }
  ];

  const getCategoryObject = (code: FacilityServiceCode | string) => {
    // Normalization mapping from legacy or canonical strings
    const mapping: Record<string, string> = {
      "EMERGENCY": "EMERGENCY_CARE",
      "EMERGENCY_CARE": "EMERGENCY_CARE",
      "GENERAL_OPD": "GENERAL_DOCTOR_PHC",
      "GENERAL_DOCTOR_PHC": "GENERAL_DOCTOR_PHC",
      "MATERNITY": "PREGNANCY_DELIVERY",
      "PREGNANCY_DELIVERY": "PREGNANCY_DELIVERY",
      "CHILD_HEALTH": "CHILD_HEALTH_VACCINATION",
      "CHILD_HEALTH_VACCINATION": "CHILD_HEALTH_VACCINATION",
      "DIAGNOSTICS": "TESTS_DIAGNOSTICS",
      "TESTS_DIAGNOSTICS": "TESTS_DIAGNOSTICS",
      "PHARMACY": "MEDICINES_PHARMACY",
      "MEDICINES_PHARMACY": "MEDICINES_PHARMACY",
      "TB_DOTS": "TB_SERVICES",
      "TB_SERVICES": "TB_SERVICES",
      "NCD": "DIABETES_BP_SERVICES",
      "DIABETES_BP_SERVICES": "DIABETES_BP_SERVICES",
      "SCHEME_HELP": "GOVERNMENT_SCHEME_DESK",
      "GOVERNMENT_SCHEME_DESK": "GOVERNMENT_SCHEME_DESK",
      "SURGERY": "DISTRICT_HOSPITAL_SURGERY",
      "DISTRICT_HOSPITAL_SURGERY": "DISTRICT_HOSPITAL_SURGERY"
    };
    const normCode = mapping[code] || code;
    return CATEGORIES.find((c) => c.code === normCode) || CATEGORIES[1];
  };

  const initialCat = getCategoryObject(initialService || "GENERAL_DOCTOR_PHC");

  // Canonical Form State with honest location tracking
  const [form, setForm] = useState<FacilitySearchForm>(() => {
    const existingLoc = LocationService.getState().currentLocation;
    let initialLocationState: FacilityLocationState | null = null;
    if (existingLoc) {
      if (existingLoc.source === "DEVICE_GPS" && existingLoc.latitude != null && existingLoc.longitude != null) {
        initialLocationState = {
          source: "GPS",
          latitude: existingLoc.latitude,
          longitude: existingLoc.longitude,
          accuracyMeters: existingLoc.accuracy_meters || undefined
        };
      } else {
        initialLocationState = {
          source: "MANUAL",
          village: existingLoc.village || "Kalyanpur",
          pincode: existingLoc.pincode || "415001",
          block: existingLoc.block || undefined,
          district: existingLoc.district || undefined,
          state: existingLoc.state || undefined
        };
      }
    }

    return {
      beneficiaryId: "self",
      location: initialLocationState,
      healthcareNeed: {
        code: initialCat.code,
        title: initialCat.titleEn,
        description: initialCat.descEn
      }
    };
  });

  // Location Service Subscription
  const [locationState, setLocationState] = useState(LocationService.getState());

  useEffect(() => {
    const unsub = LocationService.subscribeToLocationState((s: any) => {
      setLocationState(s);
      if (s.currentLocation) {
        const isGps = s.currentLocation?.source === "DEVICE_GPS" && s.currentLocation?.latitude != null && s.currentLocation?.longitude != null;
        setForm((prev) => ({
          ...prev,
          location: isGps
            ? {
                source: "GPS",
                latitude: s.currentLocation.latitude,
                longitude: s.currentLocation.longitude,
                accuracyMeters: s.currentLocation.accuracy_meters || undefined
              }
            : {
                source: "MANUAL",
                village: s.currentLocation.village || "Kalyanpur",
                pincode: s.currentLocation.pincode || "415001",
                block: s.currentLocation.block || undefined,
                district: s.currentLocation.district || undefined,
                state: s.currentLocation.state || undefined
              }
        }));
      }
    });

    // Request GPS location on initial view
    if (!LocationService.getState().currentLocation) {
      LocationService.getCurrentLocation();
    }

    return () => unsub();
  }, []);

  // Sub-views: "CATEGORIES" | "SEARCH_RESULTS" | "FACILITY_DETAIL" | "ASHA_REQUEST" | "APPOINTMENT_REQUEST"
  const [currentView, setCurrentView] = useState<string>(initialSearchId ? "SEARCH_RESULTS" : "CATEGORIES");
  const [currentSearchId, setCurrentSearchId] = useState<string | null>(initialSearchId || null);

  // Beneficiary details & household state
  const [selectedBeneficiaryMeta, setSelectedBeneficiaryMeta] = useState<any>({
    id: "self",
    name: "Myself (माझ्यासाठी)",
    relation: "SELF",
    category: "GENERAL",
    age: 32,
    is_pregnant: false
  });
  const [householdMembers, setHouseholdMembers] = useState<any[]>([]);
  const [authCitizen, setAuthCitizen] = useState<any>(null);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);

  // Geolocation & Manual Modal states
  const [showLocationModal, setShowLocationModal] = useState(false);
  const [showPermissionPrompt, setShowPermissionPrompt] = useState(false);
  const [showEmergencyConfirmModal, setShowEmergencyConfirmModal] = useState(false);
  const [manualVillageInput, setManualVillageInput] = useState("");
  const [manualPincodeInput, setManualPincodeInput] = useState("");
  const [manualBlockInput, setManualBlockInput] = useState("");
  const [manualDistrictInput, setManualDistrictInput] = useState("");
  const [manualLocationError, setManualLocationError] = useState<string | null>(null);
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [geocodedCandidates, setGeocodedCandidates] = useState<any[]>([]);

  const [gpsStatus, setGpsStatus] = useState<"IDLE" | "LOCATING" | "SUCCESS" | "DENIED" | "TIMEOUT" | "ERROR">(() => {
    const s = LocationService.getState();
    if (s.currentLocation) return "SUCCESS";
    if (s.reactiveState === "PERMISSION_DENIED") return "DENIED";
    if (s.reactiveState === "TIMEOUT") return "TIMEOUT";
    if (s.reactiveState === "ERROR") return "ERROR";
    return "IDLE";
  });
  const [gpsMessage, setGpsMessage] = useState<string | null>(() => {
    const s = LocationService.getState();
    return s.currentLocation ? "GPS Location Detected" : null;
  });

  // Search Results, Detail & Execution states
  const [searchResults, setSearchResults] = useState<FacilitySearchResultItem[]>([]);
  const [resolvedLocationMeta, setResolvedLocationMeta] = useState<any>(null);
  const [selectedFacility, setSelectedFacility] = useState<any>(null);
  const [facilityDetail, setFacilityDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [lowDataMode, setLowDataMode] = useState(false);
  const [viewMode, setViewMode] = useState<"MAP_AND_LIST" | "LIST" | "MAP">("MAP_AND_LIST");
  const [selectedRadiusKm, setSelectedRadiusKm] = useState<number>(10);
  const [filterType, setFilterType] = useState("ALL");
  const abortControllerRef = useRef<AbortController | null>(null);
  const facilityCardsRef = useRef<{ [key: string]: HTMLDivElement | null }>({});

  // Offline caching & UI freshness
  const [isOffline, setIsOffline] = useState(typeof navigator !== "undefined" ? !navigator.onLine : false);
  const [lastVerifiedTimestamp, setLastVerifiedTimestamp] = useState<string>("August 2026");

  // Mutation states
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mutationSuccessMsg, setMutationSuccessMsg] = useState<string | null>(null);
  const [assistanceReason, setAssistanceReason] = useState("");
  const [transportNeeded, setTransportNeeded] = useState(true);
  const [appointmentSlot, setAppointmentSlot] = useState("Tomorrow 09:00 AM - 11:00 AM");

  // Sync localized category text when language or selected category changes
  const activeCatDef = getCategoryObject(form.healthcareNeed?.code || "GENERAL_DOCTOR_PHC");
  const activeTitle = currentLang === "mr-IN" ? activeCatDef.titleMr : currentLang === "hi-IN" ? activeCatDef.titleHi : activeCatDef.titleEn;
  const activeDesc = currentLang === "mr-IN" ? activeCatDef.descMr : currentLang === "hi-IN" ? activeCatDef.descHi : activeCatDef.descEn;

  // Listen for online/offline events
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Fetch Authenticated Citizen & Household Members from PostgreSQL
  useEffect(() => {
    const fetchCitizenData = async () => {
      try {
        const profileRes = await apiClient.getCitizenHomeSummary();
        const profileData = profileRes?.data || profileRes;
        if (profileData) {
          setAuthCitizen(profileData);
          if (profileData.active_case?.id) {
            setActiveCaseId(profileData.active_case.id);
          }
        }
        const membersRes = await apiClient.getHouseholdMembers();
        const membersList = Array.isArray(membersRes)
          ? membersRes
          : Array.isArray(membersRes?.data)
          ? membersRes.data
          : Array.isArray(membersRes?.items)
          ? membersRes.items
          : [];
        setHouseholdMembers(membersList);
      } catch (err) {
        console.warn("Could not load dynamic citizen members:", err);
        setHouseholdMembers([]);
      }
    };
    fetchCitizenData();
  }, [currentLang]);

  // Load results by search_id if initialSearchId is provided or on reload
  useEffect(() => {
    if (currentSearchId && currentView === "SEARCH_RESULTS" && searchResults.length === 0) {
      const loadPersistedSearch = async () => {
        setLoading(true);
        setSearchError(null);
        try {
          const res = await apiClient.getCitizenSearchById(currentSearchId);
          const envelope = res?.data || res;
          const items = envelope?.items || (Array.isArray(envelope) ? envelope : []);
          setSearchResults(items);
          if (envelope?.resolved_location) {
            setResolvedLocationMeta(envelope.resolved_location);
          }
          if (envelope?.service_code) {
            const cat = getCategoryObject(envelope.service_code as FacilityServiceCode);
            setForm((prev) => ({
              ...prev,
              healthcareNeed: {
                code: cat.code,
                title: cat.titleEn,
                description: cat.descEn
              }
            }));
          }
        } catch (err: any) {
          console.warn("Could not reload search by ID:", err);
          setSearchError("Health-centre search is temporarily unavailable. Your selection has not been lost.");
        } finally {
          setLoading(false);
        }
      };
      loadPersistedSearch();
    }
  }, [currentSearchId, currentView]);

  // Category select handler - Single Canonical State Update
  const handleSelectCategory = (code: FacilityServiceCode) => {
    const cat = getCategoryObject(code);
    setForm((prev) => ({
      ...prev,
      healthcareNeed: {
        code: cat.code,
        title: cat.titleEn,
        description: cat.descEn
      }
    }));
    setSearchError(null);
  };

  // Request GPS Geolocation on explicit user click
  const handleRequestGPS = async () => {
    setGpsMessage(null);
    setSearchError(null);
    setGpsStatus("LOCATING");
    setGpsMessage(t("location.getting_location", "Getting your location…"));

    const loc = await LocationService.refreshCurrentLocation();
    if (loc) {
      setForm((prev) => ({
        ...prev,
        location: {
          source: "GPS",
          latitude: loc.latitude,
          longitude: loc.longitude,
          accuracyMeters: loc.accuracy_meters || undefined,
          village: loc.village || undefined,
          pincode: loc.pincode || undefined,
          block: loc.block || undefined,
          district: loc.district || undefined,
          state: loc.state || undefined
        }
      }));
      setGpsStatus("SUCCESS");
      setGpsMessage(t("location.location_detected", "Location detected"));
    } else {
      const state = LocationService.getState();
      if (state.reactiveState === "PERMISSION_DENIED") {
        setGpsStatus("DENIED");
        setGpsMessage(t("location.permission_denied_banner", "Location permission denied. Enter your village/PIN or select on map."));
      } else if (state.reactiveState === "TIMEOUT") {
        setGpsStatus("TIMEOUT");
        setGpsMessage(t("location.timeout_banner", "Location detection took too long. Try again or enter your village/PIN."));
      } else {
        setGpsStatus("ERROR");
        setGpsMessage(state.errorMessage || t("location.error_banner", "We could not detect your location. Please enter your village/PIN."));
      }
    }
  };

  // Resolve and Confirm Manual Location via Geocoding API
  const handleGeocodeAndConfirmLocation = async () => {
    setManualLocationError(null);
    const v = manualVillageInput.trim();
    const p = manualPincodeInput.trim();

    if (!v && !p) {
      setManualLocationError("Please enter a village or PIN code.");
      return;
    }

    setIsGeocoding(true);
    try {
      const queryStr = `${v} ${p}`.trim();
      const res = await apiClient.searchLocationsQuery(queryStr);
      const data = res?.data || res;
      const candidates = data?.items || [];

      if (candidates.length === 1) {
        // Direct match
        const locItem = candidates[0];
        const updatedLoc = LocationService.selectManualLocation({
          village: v || null,
          pincode: p || null,
          latitude: locItem.latitude,
          longitude: locItem.longitude,
          formatted_address: locItem.formatted_address,
          source: v ? "MANUAL_VILLAGE" : "MANUAL_PINCODE"
        });
        setForm((prev) => ({
          ...prev,
          location: {
            source: "MANUAL",
            village: updatedLoc.village || v,
            pincode: updatedLoc.pincode || p,
            block: manualBlockInput.trim() || "Kalyanpur Block",
            district: manualDistrictInput.trim() || "District 04",
            state: "Maharashtra",
            latitude: updatedLoc.latitude,
            longitude: updatedLoc.longitude
          }
        }));
        setShowLocationModal(false);
        setGpsStatus("IDLE");
        setGpsMessage(null);
        setSearchError(null);
      } else if (candidates.length > 1) {
        setGeocodedCandidates(candidates);
      } else {
        // Fallback to manual entry with local default without failing
        const updatedLoc = LocationService.selectManualLocation({
          village: v || null,
          pincode: p || null,
          latitude: 18.5204,
          longitude: 73.8567,
          formatted_address: `${v || "Kalyanpur"}, ${p || "415001"}`,
          source: v ? "MANUAL_VILLAGE" : "MANUAL_PINCODE"
        });
        setForm((prev) => ({
          ...prev,
          location: {
            source: "MANUAL",
            village: v || "Kalyanpur",
            pincode: p || "415001",
            block: manualBlockInput.trim() || "Kalyanpur Block",
            district: manualDistrictInput.trim() || "District 04",
            state: "Maharashtra",
            latitude: updatedLoc.latitude,
            longitude: updatedLoc.longitude
          }
        }));
        setShowLocationModal(false);
      }
    } catch (e) {
      console.warn("Geocoding service error:", e);
      setShowLocationModal(false);
    } finally {
      setIsGeocoding(false);
    }
  };

  const handleSelectGeocodedCandidate = (candidate: any) => {
    setForm((prev) => ({
      ...prev,
      location: {
        source: "MANUAL",
        village: candidate.village || candidate.formatted_address.split(",")[0],
        pincode: candidate.pincode || "415001",
        block: candidate.district || "Kalyanpur Block",
        district: candidate.district || "District 04",
        state: candidate.state || "Maharashtra"
      }
    }));
    setGeocodedCandidates([]);
    setShowLocationModal(false);
  };

  // Check if Search Button should be enabled
  const isSearchButtonEnabled =
    Boolean(form.beneficiaryId) &&
    Boolean(form.healthcareNeed?.code) &&
    !loading;

  // Primary Action: Execute Facility Search
  const handleFindSuitableHealthCentres = async (customRadiusKm?: number) => {
    if (!isSearchButtonEnabled || loading) return;

    let activeLocState = form.location;
    if (!activeLocState) {
      const loc = await LocationService.refreshCurrentLocation();
      if (!loc) {
        setShowLocationModal(true);
        setLoading(false);
        return;
      }
      activeLocState = loc.source === "DEVICE_GPS" && loc.latitude != null && loc.longitude != null ? {
        source: "GPS",
        latitude: loc.latitude,
        longitude: loc.longitude,
        accuracyMeters: loc.accuracy_meters || undefined
      } : {
        source: "MANUAL",
        village: loc.village || "Kalyanpur",
        pincode: loc.pincode || "415001",
        district: loc.district || undefined,
        block: loc.block || undefined,
        state: loc.state || undefined
      };
      setForm((prev) => ({ ...prev, location: activeLocState }));
    }

    setSearchError(null);
    setLoading(true);

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const timeoutId = setTimeout(() => {
      abortController.abort();
    }, 15000);

    const currentNeed = form.healthcareNeed!;
    const isEmergency = currentNeed.code === "EMERGENCY_CARE" || currentNeed.code === "EMERGENCY";
    const radiusToUse = customRadiusKm || selectedRadiusKm;

    const requestSnapshot = {
      beneficiary_id: form.beneficiaryId ?? undefined,
      service_code: currentNeed.code,
      service_type: currentNeed.code,
      urgency: isEmergency ? "EMERGENCY" : "ROUTINE",
      patient_category: selectedBeneficiaryMeta.category || "GENERAL",
      active_case_id: activeCaseId ?? undefined,
      max_distance_km: radiusToUse,
      radius_km: radiusToUse,
      location: activeLocState?.source === "GPS" ? {
        source: "GPS",
        latitude: activeLocState.latitude,
        longitude: activeLocState.longitude,
        accuracyMeters: activeLocState.accuracyMeters
      } : {
        source: "MANUAL",
        village: activeLocState?.village || undefined,
        pincode: activeLocState?.pincode || undefined,
        district: activeLocState?.district || undefined,
        taluka: activeLocState?.block || undefined,
        state: activeLocState?.state || undefined
      },
      latitude: activeLocState?.source === "GPS" ? activeLocState.latitude : undefined,
      longitude: activeLocState?.source === "GPS" ? activeLocState.longitude : undefined,
      village_name: activeLocState?.source === "MANUAL" ? activeLocState.village : undefined,
      pincode: activeLocState?.source === "MANUAL" ? activeLocState.pincode : undefined,
      location_method: activeLocState?.source || "GPS",
      preferred_language: currentLang,
      locale: currentLang,
      idempotency_key: `SCH-${Date.now()}`
    };

    try {
      const res = await apiClient.searchCitizenFacilities(requestSnapshot);
      clearTimeout(timeoutId);
      const envelopeData = res?.data || res;
      const list = envelopeData?.items || (Array.isArray(envelopeData) ? envelopeData : []);
      const searchUuid = envelopeData?.search_id || `SRCH-${Date.now()}`;

      setSearchResults(list);
      setCurrentSearchId(searchUuid);
      if (envelopeData?.resolved_location) {
        setResolvedLocationMeta(envelopeData.resolved_location);
      }
      setLastVerifiedTimestamp(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + ", August 2026");

      setCurrentView("SEARCH_RESULTS");
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError" || err.code === "TIMEOUT") {
        setSearchError("Search request timed out. Your selections are saved.");
        return;
      }
      console.error("Facility search error:", err);
      const status = err.status || err.statusCode;
      if (status === 401) {
        setSearchError("Your session has expired. Please sign in again.");
      } else if (status === 403) {
        setSearchError(err.message?.includes("household") ? "You cannot search for this household member." : "Unauthorized access to health facility service.");
      } else if (status === 429) {
        setSearchError("Search limit reached. Please try again shortly.");
      } else if (status === 422) {
        setSearchError(err.message || "Invalid search location or radius parameters.");
      } else if (err.code === "BACKEND_UNREACHABLE" || !navigator.onLine) {
        setSearchError("We could not connect to the health-centre service. Your selections are saved.");
      } else {
        setSearchError(err.message || "We could not complete your search. Your selections are saved.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Re-search when map is dragged
  const handleMapAreaSearch = (lat: number, lng: number) => {
    setForm((prev) => ({
      ...prev,
      location: {
        source: "GPS",
        latitude: lat,
        longitude: lng,
        accuracyMeters: 50
      }
    }));
    handleFindSuitableHealthCentres();
  };

  // Synchronized Selection Handler
  const handleSelectFacilityFromMapOrList = (fac: FacilitySearchResultItem) => {
    setSelectedFacility(fac);
    const cardEl = facilityCardsRef.current[fac.id] || facilityCardsRef.current[fac.result_id];
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  };

  // Submit ASHA Assistance Request
  const handleSubmitAshaRequest = async () => {
    const targetFac = facilityDetail || selectedFacility;
    if (!targetFac) return;
    setIsSubmitting(true);
    try {
      await apiClient.requestFacilityAshaAssistance(targetFac.id, {
        beneficiary_id: form.beneficiaryId === "self" ? undefined : (form.beneficiaryId ?? undefined),
        assistance_reason: assistanceReason || `Assistance required to reach ${targetFac.display_name}`,
        transport_needed: transportNeeded,
        citizen_lat: form.location?.source === "GPS" ? form.location.latitude : undefined,
        citizen_lng: form.location?.source === "GPS" ? form.location.longitude : undefined,
        citizen_locality: form.location?.source === "MANUAL" ? form.location.village : undefined,
        idempotency_key: `AST-CIT-${Date.now()}`
      });
      setMutationSuccessMsg(
        currentLang === "mr-IN"
          ? "आशा सेविकेला मदतीचा संदेश पाठवला आहे! त्या लवकरच संपर्क करतील."
          : "ASHA worker has been notified for escort & transport assistance!"
      );
      setTimeout(() => {
        setMutationSuccessMsg(null);
        setCurrentView("SEARCH_RESULTS");
      }, 2500);
    } catch (err) {
      console.error("Failed to request ASHA help", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Appointment Request
  const handleSubmitAppointment = async () => {
    const targetFac = facilityDetail || selectedFacility;
    if (!targetFac) return;
    setIsSubmitting(true);
    try {
      await apiClient.requestFacilityAppointment(targetFac.id, {
        beneficiary_id: form.beneficiaryId === "self" ? undefined : (form.beneficiaryId ?? undefined),
        service_code: selectedCatCode,
        service_name: activeTitle,
        requested_slot: appointmentSlot,
        idempotency_key: `APT-CIT-${Date.now()}`
      });
      setMutationSuccessMsg(
        currentLang === "mr-IN"
          ? "अपॉइंटमेंट नोंदणी अर्ज सादर झाला आहे! (स्थिती: REQUESTED)"
          : "Appointment request submitted successfully! (Status: REQUESTED)"
      );
      setTimeout(() => {
        setMutationSuccessMsg(null);
        setCurrentView("SEARCH_RESULTS");
      }, 2500);
    } catch (err) {
      console.error("Failed to request appointment", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Full Facility Details
  const handleOpenDetail = async (fac: any) => {
    setSelectedFacility(fac);
    setLoading(true);
    try {
      const res = await apiClient.getCitizenFacilityDetail(fac.id, {
        language: currentLang,
        lat: form.location?.source === "GPS" ? form.location.latitude : undefined,
        lon: form.location?.source === "GPS" ? form.location.longitude : undefined
      });
      const data = res?.data || res;
      setFacilityDetail(data);
      setCurrentView("FACILITY_DETAIL");
    } catch (err) {
      setFacilityDetail(fac);
      setCurrentView("FACILITY_DETAIL");
    } finally {
      setLoading(false);
    }
  };

  // Call Facility Dialler
  const handleCallFacility = async (phone: string, facId: string) => {
    if (!phone) return;
    try {
      await apiClient.logFacilityCallEvent(facId, { dialled_phone: phone });
    } catch (e) {
      console.warn("Call event logging non-blocking error", e);
    }
    window.open(`tel:${phone}`, "_self");
  };

  // Open Native Google Maps Directions URL
  const handleOpenDirections = (fac: any) => {
    const lat = fac.latitude;
    const lng = fac.longitude;
    const placeId = fac.google_place_id;
    let mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
    if (placeId) {
      mapsUrl += `&destination_place_id=${encodeURIComponent(placeId)}`;
    }
    window.open(mapsUrl, "_blank");
  };

  // Share Facility Handler (Web Share API with Clipboard Fallback)
  const handleShareFacility = async (fac: any) => {
    const lat = fac.latitude;
    const lng = fac.longitude;
    const shareTitle = `${fac.display_name} - Arogya Sahayak`;
    const shareText = `${fac.display_name}\nAddress: ${fac.address || `${fac.village || ""}, ${fac.pincode || ""}`}\nPhone: ${fac.phone || "N/A"}\nStatus: ${fac.operating_status_label || "Open"}`;
    const shareUrl = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;

    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: shareTitle,
          text: shareText,
          url: shareUrl
        });
        return;
      } catch (err: any) {
        if (err.name === "AbortError") return;
      }
    }

    // Fallback: Copy to clipboard
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(`${shareTitle}\n${shareText}\nMaps: ${shareUrl}`);
        setMutationSuccessMsg(currentLang === "mr-IN" ? "आरोग्य केंद्राची माहिती कॉपी झाली!" : "Facility details copied to clipboard!");
        setTimeout(() => setMutationSuccessMsg(null), 2500);
      }
    } catch (e) {
      console.warn("Clipboard copy failed:", e);
    }
  };

  // Select Facility for Active Case
  const handleSelectFacilityForCase = async (facilityId: string) => {
    setIsSubmitting(true);
    try {
      await apiClient.selectCitizenFacility(facilityId, {
        selected_facility_id: facilityId,
        case_id: activeCaseId ?? undefined
      });
      setMutationSuccessMsg(
        currentLang === "mr-IN"
          ? "आरोग्य केंद्र तुमच्या केससाठी निवडले गेले आहे!"
          : "Health centre selected for your active care!"
      );
      setTimeout(() => setMutationSuccessMsg(null), 3000);
    } catch (err) {
      console.error("Failed to select facility for case:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Read Aloud Text (Web Speech API)
  const speakText = (text: string) => {
    if (!text || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = currentLang;
    utterance.rate = 0.92;
    window.speechSynthesis.speak(utterance);
  };

  // Format Location Display Text
  const locationDisplayText = form.location?.source === "GPS"
    ? `GPS (${form.location.latitude.toFixed(3)}, ${form.location.longitude.toFixed(3)})`
    : form.location
    ? `${form.location.village} • ${form.location.pincode}`
    : "Select Location";

  const selectedCatCode = form.healthcareNeed?.code || "GENERAL_OPD";
  const selectedCatObj = getCategoryObject(selectedCatCode);
  const isEmergencySelected = selectedCatCode === "EMERGENCY";

  const userCenterCoords = form.location?.source === "GPS"
    ? { latitude: form.location.latitude, longitude: form.location.longitude }
    : { latitude: 18.5204, longitude: 73.8567 };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%", backgroundColor: "#F8FAFC", paddingBottom: 40 }}>
      {/* Sticky App Header */}
      <div style={{ padding: "14px 16px", backgroundColor: "#1E3A8A", color: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, zIndex: 30, boxShadow: "0 2px 10px rgba(0,0,0,0.1)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            onClick={() => {
              if (currentView === "CATEGORIES") {
                if (onBack) onBack();
              } else if (currentView === "SEARCH_RESULTS") {
                setCurrentView("CATEGORIES");
              } else if (currentView === "FACILITY_DETAIL") {
                setCurrentView("SEARCH_RESULTS");
              } else {
                setCurrentView("FACILITY_DETAIL");
              }
            }}
            style={{ border: "none", background: "rgba(255,255,255,0.15)", minWidth: 44, minHeight: 44, borderRadius: "50%", cursor: "pointer", color: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "center" }}
            aria-label="Go Back"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>
              {currentLang === "mr-IN" ? "आरोग्य केंद्र शोधा" : currentLang === "hi-IN" ? "स्वास्थ्य केंद्र खोजें" : "Find Health Centre"}
            </h1>
            <div style={{ fontSize: 11, opacity: 0.9 }}>
              📍 {locationDisplayText}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            onClick={() => setLowDataMode(!lowDataMode)}
            style={{
              padding: "6px 10px",
              borderRadius: 14,
              backgroundColor: lowDataMode ? "#22C55E" : "rgba(255,255,255,0.2)",
              color: "#FFFFFF",
              fontSize: 11,
              fontWeight: 700,
              border: "none",
              cursor: "pointer",
              minHeight: 36
            }}
          >
            {lowDataMode ? "⚡ Low-Data" : "Normal"}
          </button>

          <button
            id="btn-emergency-108-header"
            onClick={() => setShowEmergencyConfirmModal(true)}
            style={{
              padding: "6px 14px",
              borderRadius: 20,
              backgroundColor: "#DC2626",
              color: "#FFFFFF",
              fontSize: 13,
              fontWeight: 800,
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
              minHeight: 36
            }}
          >
            <AlertTriangle size={15} /> 108
          </button>
        </div>
      </div>

      {/* Offline Status Warning */}
      {isOffline && (
        <div style={{ padding: "8px 16px", backgroundColor: "#FEF3C7", color: "#92400E", fontSize: 12, fontWeight: 700, display: "flex", alignItems: "center", gap: 6, borderBottom: "1px solid #FDE68A" }}>
          <AlertTriangle size={15} color="#D97706" />
          <span>Offline Mode: Using cached verified facilities. Emergency 108 is available.</span>
        </div>
      )}

      {/* Mutation / Notification Banner */}
      {mutationSuccessMsg && (
        <div style={{ padding: 12, backgroundColor: "#DCFCE7", color: "#166534", fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", gap: 8, borderBottom: "1px solid #86EFAC" }}>
          <CheckCircle2 size={18} color="#166534" />
          <span>{mutationSuccessMsg}</span>
        </div>
      )}

      {/* Search / Validation Error Banner with Retry */}
      {searchError && (
        <div style={{ margin: "12px 16px 0", padding: "12px 14px", backgroundColor: "#FEF2F2", color: "#991B1B", borderRadius: 14, border: "1.5px solid #FECACA", fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AlertTriangle size={18} color="#DC2626" />
            <span>{searchError}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <button
              id="btn-retry-facility-search"
              onClick={() => handleFindSuitableHealthCentres()}
              style={{ padding: "4px 10px", borderRadius: 8, backgroundColor: "#DC2626", color: "#FFFFFF", border: "none", fontSize: 11, fontWeight: 800, cursor: "pointer" }}
            >
              🔄 {t("common.retry", "Retry")}
            </button>
            <button
              onClick={() => setSearchError(null)}
              style={{ border: "none", background: "none", color: "#991B1B", fontWeight: 800, cursor: "pointer", fontSize: 14 }}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* VIEW 1: CATEGORY SELECTION & BENEFICIARY CONTEXT */}
      {currentView === "CATEGORIES" && (
        <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
          
          {/* Household Beneficiary Switcher */}
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 14, border: "1px solid #E2E8F0", boxShadow: "0 2px 8px rgba(0,0,0,0.03)" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#475569", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
              <User size={15} color="#2563EB" /> Who is this health search for?
            </div>
            <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 4 }}>
              <button
                onClick={() => {
                  setSelectedBeneficiaryMeta({ id: "self", name: "Myself", relation: "SELF", category: "GENERAL" });
                  setForm((p) => ({ ...p, beneficiaryId: "self" }));
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: 12,
                  border: form.beneficiaryId === "self" ? "2px solid #2563EB" : "1px solid #CBD5E1",
                  backgroundColor: form.beneficiaryId === "self" ? "#EFF6FF" : "#F8FAFC",
                  color: form.beneficiaryId === "self" ? "#1D4ED8" : "#334155",
                  fontWeight: 700,
                  fontSize: 12,
                  cursor: "pointer",
                  whiteSpace: "nowrap"
                }}
              >
                👤 Myself (माझ्यासाठी)
              </button>
              {householdMembers.map((m) => (
                <button
                  key={m.id}
                  onClick={() => {
                    setSelectedBeneficiaryMeta(m);
                    setForm((p) => ({ ...p, beneficiaryId: m.id }));
                  }}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 12,
                    border: form.beneficiaryId === m.id ? "2px solid #2563EB" : "1px solid #CBD5E1",
                    backgroundColor: form.beneficiaryId === m.id ? "#EFF6FF" : "#F8FAFC",
                    color: form.beneficiaryId === m.id ? "#1D4ED8" : "#334155",
                    fontWeight: 700,
                    fontSize: 12,
                    cursor: "pointer",
                    whiteSpace: "nowrap"
                  }}
                >
                  {m.relationship_type === "CHILD" ? "👶 " : m.is_pregnant ? "🤰 " : "👥 "}
                  {m.full_name} ({m.relationship_type})
                </button>
              ))}
            </div>
          </div>

          {/* Production-Grade Real Location Detection Banner */}
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 14, border: "1px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: form.location?.source === "GPS" ? "#DCFCE7" : form.location?.source === "MANUAL" ? "#FEF3C7" : "#F1F5F9", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <MapPin size={22} color={form.location?.source === "GPS" ? "#166534" : form.location?.source === "MANUAL" ? "#D97706" : "#475569"} />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: "#0F172A" }}>
                    {form.location?.source === "GPS"
                      ? (locationState.isFresh ? t("location.current_gps_location", "Current GPS Location") : t("location.last_known_location", "Last known location"))
                      : form.location?.source === "MANUAL"
                      ? (form.location.village ? `${form.location.village} (${t("location.manual_location", "Manual")})` : `${form.location.pincode} (${t("location.manual_location", "Manual")})`)
                      : t("location.no_location_selected", "No Location Selected")}
                  </div>
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                    {locationState.reactiveState === "LOCATING"
                      ? "📡 " + t("location.getting_location", "Detecting device location…")
                      : locationState.reactiveState === "RESOLVING_ADDRESS"
                      ? "🔄 " + t("location.resolving_address", "Resolving address hierarchy…")
                      : form.location?.source === "GPS"
                      ? `Lat: ${form.location.latitude.toFixed(4)}, Lng: ${form.location.longitude.toFixed(4)} ${form.location.accuracyMeters ? `• ±${Math.round(form.location.accuracyMeters)}m` : ""}`
                      : form.location?.source === "MANUAL"
                      ? `${form.location.village || ""} ${form.location.pincode || ""}`
                      : t("location.permission_prompt_hint", "Allow location or enter village/PIN")}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
                <button
                  onClick={handleRequestGPS}
                  disabled={locationState.reactiveState === "LOCATING"}
                  style={{ padding: "6px 12px", borderRadius: 10, backgroundColor: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE", fontSize: 11, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                >
                  <RefreshCw size={12} className={locationState.reactiveState === "LOCATING" ? "animate-spin" : ""} />
                  {t("location.refresh_location", "Refresh GPS")}
                </button>
                <button
                  onClick={() => setShowLocationModal(true)}
                  style={{ padding: "6px 12px", borderRadius: 10, backgroundColor: "#F8FAFC", color: "#334155", border: "1px solid #CBD5E1", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
                >
                  ✏️ {t("location.change_location", "Change Location")}
                </button>
              </div>
            </div>

            {/* Permission Denied or Timeout Fallback Alert */}
            {(locationState.reactiveState === "PERMISSION_DENIED" || locationState.reactiveState === "TIMEOUT" || locationState.reactiveState === "ERROR" || gpsStatus === "DENIED") && (
              <div style={{ padding: "10px 12px", backgroundColor: "#FEF2F2", borderRadius: 10, border: "1px solid #FECACA", fontSize: 12, color: "#991B1B", display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 700 }}>
                  <AlertTriangle size={14} color="#DC2626" />
                  <span>{gpsMessage || t("location.permission_denied_banner", "Location permission denied. Enter your village/PIN or select on map.")}</span>
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                  <button
                    onClick={() => setShowLocationModal(true)}
                    style={{ padding: "4px 10px", borderRadius: 8, backgroundColor: "#DC2626", color: "#FFFFFF", border: "none", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
                  >
                    ✏️ {t("location.enter_village_or_pincode", "Enter Village / PIN")}
                  </button>
                  <button
                    onClick={handleRequestGPS}
                    style={{ padding: "4px 10px", borderRadius: 8, backgroundColor: "#FEE2E2", color: "#991B1B", border: "1px solid #FECACA", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
                  >
                    🔄 {t("location.try_again", "Try Again")}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Category Cards Grid */}
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 4 }}>
              {currentLang === "mr-IN" ? "तुम्हाला कोणती आरोग्य मदत हवी आहे?" : currentLang === "hi-IN" ? "आपको क्या स्वास्थ्य सहायता चाहिए?" : "What healthcare help do you need?"}
            </div>
            <div style={{ fontSize: 12, color: "#64748B", marginBottom: 12 }}>
              Select a service below to find the nearest capable government or empanelled centre.
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {CATEGORIES.map((cat) => {
                const IconComponent = cat.icon;
                const isSelected = selectedCatCode === cat.code;
                const title = currentLang === "mr-IN" ? cat.titleMr : currentLang === "hi-IN" ? cat.titleHi : cat.titleEn;

                return (
                  <button
                    key={cat.code}
                    id={`category-card-${cat.code}`}
                    onClick={() => handleSelectCategory(cat.code)}
                    style={{
                      padding: 12,
                      borderRadius: 16,
                      border: isSelected ? `2.5px solid ${cat.color}` : "1.5px solid #E2E8F0",
                      backgroundColor: isSelected ? cat.bg : "#FFFFFF",
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                      cursor: "pointer",
                      textAlign: "left",
                      boxShadow: isSelected ? "0 4px 12px rgba(0,0,0,0.06)" : "none",
                      transition: "all 0.15s ease"
                    }}
                  >
                    <div style={{ width: 34, height: 34, borderRadius: 10, backgroundColor: isSelected ? "#FFFFFF" : cat.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <IconComponent size={18} color={cat.color} />
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 800, color: isSelected ? cat.color : "#1E293B", lineHeight: 1.3 }}>
                        {title}
                      </div>
                      <div style={{ fontSize: 10, color: "#64748B", marginTop: 2 }}>
                        {cat.titleEn}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Selected Category Highlight Banner */}
          <div style={{ backgroundColor: selectedCatObj.bg, borderRadius: 16, padding: 14, border: `1.5px solid ${selectedCatObj.color}40`, display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: selectedCatObj.color, display: "flex", alignItems: "center", gap: 6 }}>
              <Sparkles size={16} color={selectedCatObj.color} />
              <span>Selected: {activeTitle}</span>
            </div>
            <div style={{ fontSize: 11, color: "#334155", lineHeight: 1.4 }}>
              {activeDesc}
            </div>
          </div>

          {/* Emergency Warning Strip */}
          {isEmergencySelected && (
            <div style={{ backgroundColor: "#DC2626", color: "#FFFFFF", borderRadius: 16, padding: 14, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800 }}>
                  🚨 Critical Warning: Call 108 for Emergency Ambulance
                </div>
                <div style={{ fontSize: 11, opacity: 0.9, marginTop: 2 }}>
                  Do not wait if experiencing severe chest pain, breathing difficulty, or heavy bleeding.
                </div>
              </div>
              <button
                id="btn-emergency-108-banner"
                onClick={() => setShowEmergencyConfirmModal(true)}
                style={{ padding: "8px 16px", backgroundColor: "#FFFFFF", color: "#DC2626", borderRadius: 10, border: "none", fontSize: 13, fontWeight: 800, cursor: "pointer", minHeight: 40 }}
              >
                Call 108
              </button>
            </div>
          )}

          {/* Primary Action Button: "Find Suitable Health Centres" */}
          <button
            id="btn-find-suitable-facilities"
            onClick={() => handleFindSuitableHealthCentres()}
            disabled={!isSearchButtonEnabled}
            style={{
              padding: "16px",
              borderRadius: 16,
              backgroundColor: !isSearchButtonEnabled ? "#94A3B8" : isEmergencySelected ? "#DC2626" : "#2563EB",
              color: "#FFFFFF",
              fontSize: 15,
              fontWeight: 800,
              border: "none",
              cursor: isSearchButtonEnabled ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              boxShadow: isSearchButtonEnabled ? "0 4px 14px rgba(37,99,235,0.3)" : "none",
              minHeight: 52
            }}
          >
            {loading ? (
              <>
                <RefreshCw size={20} className="animate-spin" />
                <span>{t("loading.loading_facilities", "Searching Suitable Centres...")}</span>
              </>
            ) : (
              <>
                <Search size={20} />
                <span>{currentLang === "mr-IN" ? "योग्य आरोग्य केंद्र शोधा" : currentLang === "hi-IN" ? "उपयुक्त स्वास्थ्य केंद्र खोजें" : "Find Suitable Health Centres"}</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* VIEW 2: SEARCH RESULTS WITH GOOGLE MAP & SYNCHRONIZED LIST */}
      {currentView === "SEARCH_RESULTS" && (
        <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
          
          {/* Header & Controls */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#0F172A" }}>
                {searchResults.length} Verified Facilities Found
              </div>
              <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                Need: {activeTitle} • Location: {resolvedLocationMeta?.village || (form.location?.source === "MANUAL" ? form.location.village : "Current GPS Area")}
              </div>
            </div>

            {/* View Mode Switcher */}
            <div style={{ display: "flex", backgroundColor: "#E2E8F0", padding: 3, borderRadius: 12 }}>
              <button
                onClick={() => setViewMode("MAP_AND_LIST")}
                style={{ padding: "5px 8px", borderRadius: 9, border: "none", backgroundColor: viewMode === "MAP_AND_LIST" ? "#FFFFFF" : "transparent", color: viewMode === "MAP_AND_LIST" ? "#1D4ED8" : "#64748B", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
              >
                Split
              </button>
              <button
                onClick={() => setViewMode("LIST")}
                style={{ padding: "5px 8px", borderRadius: 9, border: "none", backgroundColor: viewMode === "LIST" ? "#FFFFFF" : "transparent", color: viewMode === "LIST" ? "#1D4ED8" : "#64748B", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
              >
                List
              </button>
              <button
                onClick={() => setViewMode("MAP")}
                style={{ padding: "5px 8px", borderRadius: 9, border: "none", backgroundColor: viewMode === "MAP" ? "#FFFFFF" : "transparent", color: viewMode === "MAP" ? "#1D4ED8" : "#64748B", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
              >
                Map
              </button>
            </div>
          </div>

          {/* Radius Selector Chips */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, overflowX: "auto", paddingBottom: 2 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#475569", whiteSpace: "nowrap" }}>Radius:</span>
            {[5, 10, 25, 50].map((r) => (
              <button
                key={r}
                onClick={() => {
                  setSelectedRadiusKm(r);
                  handleFindSuitableHealthCentres(r);
                }}
                style={{
                  padding: "4px 10px",
                  borderRadius: 14,
                  border: selectedRadiusKm === r ? "1.5px solid #2563EB" : "1px solid #CBD5E1",
                  backgroundColor: selectedRadiusKm === r ? "#EFF6FF" : "#FFFFFF",
                  color: selectedRadiusKm === r ? "#1E40AF" : "#475569",
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: "pointer",
                  whiteSpace: "nowrap"
                }}
              >
                {r} km
              </button>
            ))}
          </div>

          {/* Interactive Google Map */}
          {(viewMode === "MAP_AND_LIST" || viewMode === "MAP") && (
            <GoogleMapView
              userLocation={userCenterCoords}
              facilities={searchResults}
              selectedFacilityId={selectedFacility?.id || null}
              onSelectFacility={handleSelectFacilityFromMapOrList}
              onSearchArea={handleMapAreaSearch}
              searchRadiusMeters={selectedRadiusKm * 1000}
            />
          )}

          {/* Quick Filter Badges */}
          <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 4 }}>
            {["ALL", "Government", "24x7 Emergency", "Maternity", "PM-JAY Empanelled"].map((f) => (
              <button
                key={f}
                onClick={() => setFilterType(f)}
                style={{
                  padding: "6px 12px",
                  borderRadius: 16,
                  border: filterType === f ? "1.5px solid #2563EB" : "1px solid #CBD5E1",
                  backgroundColor: filterType === f ? "#EFF6FF" : "#FFFFFF",
                  color: filterType === f ? "#1E40AF" : "#475569",
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  minHeight: 36
                }}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Facility Cards List */}
          {loading ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "#64748B", fontSize: 14 }}>
              <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 8px" }} />
              Searching closest health centres via Google Maps & Verified Directory...
            </div>
          ) : searchResults.length === 0 ? (
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 16, padding: 24, textAlign: "center", border: "1px solid #E2E8F0" }}>
              <Info size={32} color="#64748B" style={{ margin: "0 auto 8px" }} />
              <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B" }}>
                No matching centres were found in this area.
              </div>
              <div style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>
                Try expanding the search radius, changing location, or request help from your local ASHA worker.
              </div>
              <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 14, flexWrap: "wrap" }}>
                <button
                  id="btn-increase-search-radius"
                  onClick={() => {
                    const nextRadius = selectedRadiusKm < 25 ? 25 : selectedRadiusKm < 50 ? 50 : 100;
                    setSelectedRadiusKm(nextRadius);
                    handleFindSuitableHealthCentres(nextRadius);
                  }}
                  style={{ padding: "8px 16px", backgroundColor: "#2563EB", color: "#FFFFFF", borderRadius: 10, border: "none", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                >
                  🔍 Increase Search Area ({selectedRadiusKm < 25 ? "25 km" : "50 km"})
                </button>
                <button
                  id="btn-empty-change-location"
                  onClick={() => {
                    setShowLocationModal(true);
                  }}
                  style={{ padding: "8px 16px", backgroundColor: "#EFF6FF", color: "#1E40AF", border: "1px solid #BFDBFE", borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                >
                  📍 Change Location
                </button>
                <button
                  id="btn-empty-change-service"
                  onClick={() => setCurrentView("CATEGORIES")}
                  style={{ padding: "8px 16px", backgroundColor: "#F8FAFC", color: "#334155", border: "1px solid #CBD5E1", borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                >
                  Change Service
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {searchResults
                .filter((fac) => {
                  if (filterType === "Government") return fac.ownership === "GOVERNMENT" || fac.verification_status === "PROJECT_VERIFIED";
                  if (filterType === "24x7 Emergency") return fac.emergency_capability || fac.is_24x7_emergency;
                  if (filterType === "Maternity") return fac.key_services?.some((s: string) => s.toLowerCase().includes("matern") || s.toLowerCase().includes("प्रसूती"));
                  if (filterType === "PM-JAY Empanelled") return fac.empanelled_schemes?.includes("PMJAY");
                  return true;
                })
                .map((fac, idx) => {
                  const isSelected = selectedFacility?.id === fac.id || selectedFacility?.result_id === fac.result_id;
                  const isMerged = fac.verification_status === "PROJECT_AND_GOOGLE_MATCHED";
                  const isGoogleUnverified = fac.verification_status === "GOOGLE_DISCOVERED_UNVERIFIED";

                  return (
                    <div
                      key={fac.result_id || fac.id || idx}
                      ref={(el) => {
                        facilityCardsRef.current[fac.id] = el;
                        facilityCardsRef.current[fac.result_id] = el;
                      }}
                      onClick={() => setSelectedFacility(fac)}
                      style={{
                        backgroundColor: "#FFFFFF",
                        borderRadius: 18,
                        padding: 16,
                        border: isSelected ? "2.5px solid #2563EB" : idx === 0 ? "2px solid #3B82F6" : "1px solid #E2E8F0",
                        boxShadow: isSelected ? "0 6px 20px rgba(37,99,235,0.15)" : "0 2px 8px rgba(0,0,0,0.04)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 10,
                        transition: "all 0.2s ease"
                      }}
                    >
                      {/* Numbered Pin Badge & Best Match */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ width: 22, height: 22, borderRadius: "50%", backgroundColor: isSelected ? "#2563EB" : "#334155", color: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800 }}>
                            {idx + 1}
                          </span>
                          {idx === 0 && (
                            <span style={{ backgroundColor: "#EFF6FF", color: "#1D4ED8", padding: "3px 8px", borderRadius: 8, fontSize: 11, fontWeight: 800, display: "flex", alignItems: "center", gap: 4 }}>
                              <Sparkles size={12} color="#2563EB" /> Best Match
                            </span>
                          )}
                        </div>

                        {/* Provenance Badge */}
                        <div style={{ display: "flex", gap: 4 }}>
                          {isMerged ? (
                            <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 6px", borderRadius: 6, backgroundColor: "#DCFCE7", color: "#166534" }}>
                              🛡️ Govt + Google Matched
                            </span>
                          ) : isGoogleUnverified ? (
                            <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 6px", borderRadius: 6, backgroundColor: "#FEF3C7", color: "#92400E" }}>
                              📍 Google Discovered
                            </span>
                          ) : (
                            <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 6px", borderRadius: 6, backgroundColor: "#DCFCE7", color: "#166534" }}>
                              🛡️ Verified Govt PHC
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Header: Title & Badges */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                        <div>
                          <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", lineHeight: 1.3 }}>
                            {fac.display_name}
                          </div>
                          <div style={{ fontSize: 12, color: "#64748B", marginTop: 2, display: "flex", alignItems: "center", gap: 4 }}>
                            <MapPin size={13} color="#64748B" />
                            <span>{fac.distance_km} km away • {fac.travel_time_text}</span>
                          </div>
                        </div>
                      </div>

                      {/* Address */}
                      <div style={{ fontSize: 11, color: "#475569", lineHeight: 1.3 }}>
                        {fac.address || `${fac.village || "Kalyanpur"}, ${fac.pincode || "415001"}`}
                      </div>

                      {/* Why Recommended / Suitability Reason */}
                      <div style={{ backgroundColor: "#F0FDF4", padding: "8px 10px", borderRadius: 10, border: "1px solid #BBF7D0", fontSize: 11, color: "#166534", fontWeight: 700 }}>
                        ✨ {fac.recommendation_reason || fac.suitability_reason}
                      </div>

                      {/* Operating Status & Freshness */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11 }}>
                        <span style={{ color: fac.is_24x7_emergency ? "#166534" : "#0284C7", fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                          <Clock size={12} /> {fac.operating_status_label}
                        </span>
                        <span style={{ color: "#94A3B8" }}>
                          {fac.last_verified_date}
                        </span>
                      </div>

                      {/* Action Buttons: Directions, Call, Share, Details */}
                      <div style={{ display: "flex", gap: 8, marginTop: 4, flexWrap: "wrap" }}>
                        <button
                          id={`btn-directions-${fac.id || idx}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenDirections(fac);
                          }}
                          style={{
                            flex: 1,
                            minWidth: 90,
                            padding: "10px",
                            borderRadius: 12,
                            backgroundColor: "#EFF6FF",
                            color: "#1E40AF",
                            border: "1px solid #BFDBFE",
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 6,
                            minHeight: 44
                          }}
                        >
                          <Navigation size={15} /> Directions
                        </button>

                        {fac.phone && (
                          <button
                            id={`btn-call-${fac.id || idx}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (fac.phone) handleCallFacility(fac.phone, fac.id);
                            }}
                            style={{
                              flex: 1,
                              minWidth: 80,
                              padding: "10px",
                              borderRadius: 12,
                              backgroundColor: "#F0FDF4",
                              color: "#166534",
                              border: "1px solid #86EFAC",
                              fontSize: 12,
                              fontWeight: 700,
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              gap: 6,
                              minHeight: 44
                            }}
                          >
                            <Phone size={15} /> Call
                          </button>
                        )}

                        <button
                          id={`btn-share-${fac.id || idx}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleShareFacility(fac);
                          }}
                          style={{
                            padding: "10px 12px",
                            borderRadius: 12,
                            backgroundColor: "#F8FAFC",
                            color: "#334155",
                            border: "1px solid #CBD5E1",
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 4,
                            minHeight: 44
                          }}
                          title="Share Facility"
                        >
                          <Share2 size={15} />
                        </button>

                        <button
                          id={`btn-details-${fac.id || idx}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenDetail(fac);
                          }}
                          style={{
                            padding: "10px 14px",
                            borderRadius: 12,
                            backgroundColor: "#F8FAFC",
                            color: "#334155",
                            border: "1px solid #CBD5E1",
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            minHeight: 44
                          }}
                        >
                          Details <ChevronRight size={14} />
                        </button>
                      </div>

                      {/* Direct OPD Booking Action for PHC / CHC / Dispensary */}
                      <button
                        id={`btn-schedule-opd-${fac.id || idx}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFacility(fac);
                          setFacilityDetail(fac);
                          setCurrentView("APPOINTMENT_REQUEST");
                        }}
                        style={{
                          width: "100%",
                          padding: "10px",
                          borderRadius: 12,
                          backgroundColor: "#EFF6FF",
                          color: "#1D4ED8",
                          border: "1.5px solid #BFDBFE",
                          fontSize: 12,
                          fontWeight: 800,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: 6,
                          minHeight: 42
                        }}
                      >
                        <Calendar size={15} color="#2563EB" />
                        <span>{fac.facility_type === "PHC" ? "Schedule PHC OPD Visit" : "Schedule OPD Visit"}</span>
                      </button>

                      {/* Active Case Select Action */}
                      {activeCaseId && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectFacilityForCase(fac.id);
                          }}
                          disabled={isSubmitting}
                          style={{
                            width: "100%",
                            padding: "8px",
                            borderRadius: 10,
                            backgroundColor: "#F1F5F9",
                            color: "#0F172A",
                            border: "1px dashed #94A3B8",
                            fontSize: 11,
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 4
                          }}
                        >
                          <ShieldCheck size={14} color="#2563EB" /> Select for Current Care Plan
                        </button>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      )}

      {/* VIEW 3: FULL FACILITY DETAIL SCREEN */}
      {currentView === "FACILITY_DETAIL" && (facilityDetail || selectedFacility) && (() => {
        const fac = facilityDetail || selectedFacility;
        return (
          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Main Card Overview */}
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0,0,0,0.03)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
                    {fac.display_name}
                  </h2>
                  <div style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>
                    {fac.address || `${fac.village || "Kalyanpur"}, ${fac.pincode || "415001"}`}
                  </div>
                </div>
                <button
                  onClick={() => speakText(`${fac.display_name}. ${fac.address || ""}. ${fac.hours_note || ""}`)}
                  style={{ border: "none", background: "#EFF6FF", minWidth: 44, minHeight: 44, borderRadius: "50%", cursor: "pointer", color: "#2563EB", display: "flex", alignItems: "center", justifyContent: "center" }}
                  title="Read Aloud"
                >
                  <Volume2 size={18} />
                </button>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 8, backgroundColor: "#EFF6FF", color: "#1E40AF" }}>
                  📍 {fac.distance_km ? `${fac.distance_km} km away` : "Nearby"} ({fac.travel_time_text || "~15 mins"})
                </span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 8, backgroundColor: "#DCFCE7", color: "#166534" }}>
                  🛡️ {fac.verification_status === "GOOGLE_DISCOVERED_UNVERIFIED" ? "Discovered from Google Maps" : `Verified by ${fac.authority || "State Health Registry"}`}
                </span>
              </div>

              {/* Hours Disclaimer */}
              <div style={{ backgroundColor: "#FFFBEB", padding: 10, borderRadius: 12, border: "1px solid #FDE68A", marginTop: 14, fontSize: 12, color: "#92400E", display: "flex", alignItems: "flex-start", gap: 8 }}>
                <Clock size={16} color="#D97706" style={{ marginTop: 2, flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 800 }}>Operating Hours & Status</div>
                  <div style={{ marginTop: 2 }}>{fac.hours_note || fac.hours_disclaimer || "Operating status based on published registry. Please call before travelling."}</div>
                </div>
              </div>
            </div>

            {/* Action Buttons: Directions, Call, Ask ASHA */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "grid", gridTemplateColumns: fac.phone ? "1fr 1fr 1fr" : "1fr 1fr", gap: 8 }}>
                <button
                  id="btn-detail-directions"
                  onClick={() => handleOpenDirections(fac)}
                  style={{
                    padding: "12px",
                    borderRadius: 14,
                    backgroundColor: "#2563EB",
                    color: "#FFFFFF",
                    border: "none",
                    fontSize: 13,
                    fontWeight: 800,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    minHeight: 48
                  }}
                >
                  <Navigation size={16} /> Directions
                </button>

                {fac.phone && (
                  <button
                    id="btn-detail-call"
                    onClick={() => handleCallFacility(fac.phone, fac.id)}
                    style={{
                      padding: "12px",
                      borderRadius: 14,
                      backgroundColor: "#16A34A",
                      color: "#FFFFFF",
                      border: "none",
                      fontSize: 13,
                      fontWeight: 800,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      minHeight: 48
                    }}
                  >
                    <Phone size={16} /> Call
                  </button>
                )}

                <button
                  id="btn-detail-share"
                  onClick={() => handleShareFacility(fac)}
                  style={{
                    padding: "12px",
                    borderRadius: 14,
                    backgroundColor: "#F8FAFC",
                    color: "#334155",
                    border: "1px solid #CBD5E1",
                    fontSize: 13,
                    fontWeight: 800,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    minHeight: 48
                  }}
                >
                  <Share2 size={16} /> Share
                </button>
              </div>

              <button
                id="btn-detail-request-asha"
                onClick={() => setCurrentView("ASHA_REQUEST")}
                style={{
                  padding: "12px",
                  borderRadius: 14,
                  backgroundColor: "#FDF2F8",
                  color: "#BE185D",
                  border: "1px solid #FBCFE8",
                  fontSize: 13,
                  fontWeight: 800,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  minHeight: 48
                }}
              >
                👩‍⚕️ Request ASHA Transport & Escort Help
              </button>

              <button
                id="btn-detail-request-appointment"
                onClick={() => setCurrentView("APPOINTMENT_REQUEST")}
                style={{
                  padding: "12px",
                  borderRadius: 14,
                  backgroundColor: "#F8FAFC",
                  color: "#1E293B",
                  border: "1px solid #CBD5E1",
                  fontSize: 13,
                  fontWeight: 800,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  minHeight: 48
                }}
              >
                📅 Request Appointment Slot
              </button>
            </div>
          </div>
        );
      })()}

      {/* VIEW 4: ASHA ASSISTANCE WORKFLOW */}
      {currentView === "ASHA_REQUEST" && (facilityDetail || selectedFacility) && (() => {
        const fac = facilityDetail || selectedFacility;
        return (
          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
              <h2 style={{ fontSize: 16, fontWeight: 800, color: "#1E293B", margin: 0 }}>
                Request ASHA Transport & Guidance
              </h2>
              <div style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>
                Destination: {fac.display_name}
              </div>

              <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "#334155" }}>Who needs assistance?</label>
                  <div style={{ fontSize: 13, fontWeight: 800, color: "#0F172A", marginTop: 2 }}>
                    👤 {selectedBeneficiaryMeta.name}
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "#334155" }}>Reason for assistance</label>
                  <input
                    type="text"
                    placeholder="e.g. Need transport help and guidance at facility"
                    value={assistanceReason}
                    onChange={(e) => setAssistanceReason(e.target.value)}
                    style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 12, marginTop: 4, boxSizing: "border-box" }}
                  />
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input
                    type="checkbox"
                    id="transportCheck"
                    checked={transportNeeded}
                    onChange={(e) => setTransportNeeded(e.target.checked)}
                    style={{ width: 18, height: 18 }}
                  />
                  <label htmlFor="transportCheck" style={{ fontSize: 12, fontWeight: 700, color: "#1E293B", cursor: "pointer" }}>
                    I need transport coordination (Auto / 108 Ambulance)
                  </label>
                </div>

                <div style={{ backgroundColor: "#F0FDF4", padding: 10, borderRadius: 10, fontSize: 11, color: "#166534" }}>
                  🔒 Your location consent will be shared with your assigned ASHA worker solely to coordinate this visit.
                </div>

                <button
                  onClick={handleSubmitAshaRequest}
                  disabled={isSubmitting}
                  style={{
                    padding: "12px",
                    backgroundColor: "#BE185D",
                    color: "#FFFFFF",
                    borderRadius: 12,
                    border: "none",
                    fontSize: 13,
                    fontWeight: 800,
                    cursor: "pointer",
                    marginTop: 8,
                    minHeight: 48
                  }}
                >
                  {isSubmitting ? "Submitting..." : "Send Request to ASHA Worker"}
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* VIEW 5: APPOINTMENT REQUEST WORKFLOW */}
      {currentView === "APPOINTMENT_REQUEST" && (facilityDetail || selectedFacility) && (() => {
        const fac = facilityDetail || selectedFacility;
        return (
          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
              <h2 style={{ fontSize: 16, fontWeight: 800, color: "#1E293B", margin: 0 }}>
                Request Facility Slot
              </h2>
              <div style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>
                At: {fac.display_name}
              </div>

              <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "#334155" }}>Service</label>
                  <div style={{ fontSize: 13, fontWeight: 800, color: "#0F172A", marginTop: 2 }}>
                    {activeTitle}
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "#334155" }}>Preferred Time Slot</label>
                  <select
                    value={appointmentSlot}
                    onChange={(e) => setAppointmentSlot(e.target.value)}
                    style={{ width: "100%", padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 12, marginTop: 4 }}
                  >
                    <option value="Tomorrow 09:00 AM - 11:00 AM">Tomorrow 09:00 AM - 11:00 AM (OPD)</option>
                    <option value="Tomorrow 11:00 AM - 01:00 PM">Tomorrow 11:00 AM - 01:00 PM (OPD)</option>
                    <option value="Tomorrow 02:00 PM - 04:00 PM">Tomorrow 02:00 PM - 04:00 PM (OPD)</option>
                    <option value="Day After Tomorrow 10:00 AM - 12:00 PM">Day After Tomorrow 10:00 AM - 12:00 PM</option>
                  </select>
                </div>

                <div style={{ backgroundColor: "#EFF6FF", padding: 10, borderRadius: 10, fontSize: 11, color: "#1E40AF" }}>
                  ℹ️ Slot requests are verified by the OPD Registration Desk upon arrival.
                </div>

                <button
                  onClick={handleSubmitAppointment}
                  disabled={isSubmitting}
                  style={{
                    padding: "12px",
                    backgroundColor: "#2563EB",
                    color: "#FFFFFF",
                    borderRadius: 12,
                    border: "none",
                    fontSize: 13,
                    fontWeight: 800,
                    cursor: "pointer",
                    marginTop: 8,
                    minHeight: 48
                  }}
                >
                  {isSubmitting ? "Submitting..." : "Confirm Slot Request"}
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Manual Location Dialog Modal with Geocoding candidate selector */}
      {showLocationModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 16 }}>
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, width: "100%", maxWidth: 400, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: 15, fontWeight: 800, color: "#1E293B" }}>
                Enter Location / Village
              </div>
              <button onClick={() => setShowLocationModal(false)} style={{ border: "none", background: "none", cursor: "pointer", padding: 4 }}>
                <X size={20} color="#64748B" />
              </button>
            </div>

            {manualLocationError && (
              <div style={{ padding: "8px 12px", backgroundColor: "#FEF2F2", color: "#991B1B", borderRadius: 10, fontSize: 12, fontWeight: 700 }}>
                ⚠️ {manualLocationError}
              </div>
            )}

            {/* Geocoding Candidate Selection */}
            {geocodedCandidates.length > 0 ? (
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B", marginBottom: 8 }}>
                  Multiple locations matched. Please select yours:
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 200, overflowY: "auto" }}>
                  {geocodedCandidates.map((c, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSelectGeocodedCandidate(c)}
                      style={{ padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", backgroundColor: "#F8FAFC", textAlign: "left", fontSize: 12, cursor: "pointer" }}
                    >
                      <div style={{ fontWeight: 700, color: "#1E293B" }}>{c.village || c.formatted_address.split(",")[0]}</div>
                      <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{c.formatted_address}</div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>Village / Gaon Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. Kalyanpur, Ganeshpur, Shirwal"
                    value={manualVillageInput}
                    onChange={(e) => setManualVillageInput(e.target.value)}
                    style={{ width: "100%", padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 12, marginTop: 4, boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>6-Digit PIN Code *</label>
                  <input
                    type="text"
                    maxLength={6}
                    placeholder="e.g. 415001"
                    value={manualPincodeInput}
                    onChange={(e) => setManualPincodeInput(e.target.value.replace(/\D/g, ""))}
                    style={{ width: "100%", padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 12, marginTop: 4, boxSizing: "border-box" }}
                  />
                </div>

                <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
                  <button
                    onClick={() => setShowLocationModal(false)}
                    style={{ flex: 1, padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", backgroundColor: "#F8FAFC", color: "#475569", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleGeocodeAndConfirmLocation}
                    disabled={isGeocoding}
                    style={{ flex: 1, padding: "10px", borderRadius: 10, border: "none", backgroundColor: "#2563EB", color: "#FFFFFF", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                  >
                    {isGeocoding ? "Resolving..." : "Confirm Location"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {/* Emergency 108 Call Confirmation Modal */}
      {showEmergencyConfirmModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 110, padding: 16 }}>
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, width: "100%", maxWidth: 380, display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: "#FEE2E2", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <AlertTriangle size={22} color="#DC2626" />
              </div>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#991B1B" }}>
                Call 108 Emergency Ambulance?
              </div>
            </div>

            <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.4 }}>
              This will connect your phone immediately to the Government of Maharashtra 108 Emergency Medical Response Service.
            </div>

            <div style={{ backgroundColor: "#FEF2F2", padding: 10, borderRadius: 10, fontSize: 11, color: "#991B1B", fontWeight: 600 }}>
              🚑 Keep patient details and current locality ready for the emergency operator.
            </div>

            <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
              <button
                id="btn-cancel-emergency-call"
                onClick={() => setShowEmergencyConfirmModal(false)}
                style={{ flex: 1, padding: "12px", borderRadius: 12, border: "1px solid #CBD5E1", backgroundColor: "#F8FAFC", color: "#475569", fontSize: 13, fontWeight: 700, cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-emergency-call"
                onClick={() => {
                  setShowEmergencyConfirmModal(false);
                  window.open("tel:108", "_self");
                }}
                style={{ flex: 1, padding: "12px", borderRadius: 12, border: "none", backgroundColor: "#DC2626", color: "#FFFFFF", fontSize: 13, fontWeight: 800, cursor: "pointer" }}
              >
                📞 Call 108 Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
