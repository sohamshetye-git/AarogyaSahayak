import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  Award, Search, ChevronRight, CheckCircle2, AlertCircle, FileText,
  ArrowLeft, Volume2, User, Users, ShieldCheck, HeartPulse,
  Phone, MapPin, Building2, ExternalLink, Bookmark, BookmarkCheck,
  HelpCircle, RefreshCw, Clock, ArrowRight, UserPlus, Info, Check,
  X, AlertTriangle, Stethoscope, Baby, HeartHandshake, Pill, Activity,
  Accessibility, IndianRupee, Smile, Heart, Filter, Send, Share2, Globe,
  Navigation, Navigation2, Compass, Radio, Map
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";
import { useCitizenAuth } from "../context/CitizenAuthContext";
import {
  SchemeCategoryDTO, SchemeListItemDTO, SchemeDetailDTO, SchemeApplicationGuidanceDTO,
  SchemeHelpRequirementsDTO, SchemeHelpCentreItemDTO, SchemeHelpCentresResponseDTO, SchemeFacilityDetailDTO
} from "@aarogya/shared-types";
import { LocationService, LocationData } from "@aarogya/location";
import { GoogleMapView } from "./GoogleMapView";

interface SchemesScreenProps {
  onBack?: () => void;
  onNavigateToFacilities?: () => void;
  onNavigateToAsha?: () => void;
}

// Canonical URL & Flow Routes
type SchemeRoute =
  | { type: "categories" }
  | { type: "category_list"; categoryId: string }
  | { type: "scheme_detail"; schemeId: string }
  | { type: "eligibility"; schemeId: string }
  | { type: "how_to_apply"; schemeId: string }
  | { type: "check_beneficiary" }
  | { type: "all_screening_results" }
  | { type: "saved_schemes" }
  | { type: "applications" }
  | { type: "help_centres"; schemeId: string }
  | { type: "help_centre_detail"; schemeId: string; facilityId: string };


export const SchemesScreen: React.FC<SchemesScreenProps> = ({
  onBack,
  onNavigateToFacilities,
  onNavigateToAsha
}) => {
  const { t, locale } = useLanguage();

  // Route State synchronized with browser URL
  const [routeState, setRouteState] = useState<SchemeRoute>(() => {
    const path = window.location.pathname;
    if (path.includes("/citizen/schemes/category/")) {
      const parts = path.split("/citizen/schemes/category/");
      const catId = parts[1]?.split("/")[0]?.split("?")[0];
      if (catId) return { type: "category_list", categoryId: decodeURIComponent(catId) };
    } else if (path.includes("/help-centres/")) {
      const parts = path.split("/citizen/schemes/")[1]?.split("/help-centres/");
      if (parts && parts[0] && parts[1]) {
        return { type: "help_centre_detail", schemeId: decodeURIComponent(parts[0]), facilityId: decodeURIComponent(parts[1]) };
      }
    } else if (path.includes("/help-centres")) {
      const match = path.match(/\/citizen\/schemes\/([^/]+)\/help-centres/);
      if (match && match[1]) return { type: "help_centres", schemeId: decodeURIComponent(match[1]) };
    } else if (path.includes("/eligibility")) {
      const match = path.match(/\/citizen\/schemes\/([^/]+)\/eligibility/);
      if (match && match[1]) return { type: "eligibility", schemeId: decodeURIComponent(match[1]) };
    } else if (path.includes("/how-to-apply")) {
      const match = path.match(/\/citizen\/schemes\/([^/]+)\/how-to-apply/);
      if (match && match[1]) return { type: "how_to_apply", schemeId: decodeURIComponent(match[1]) };
    } else if (path.startsWith("/citizen/schemes/")) {
      const sId = path.replace("/citizen/schemes/", "").split("/")[0]?.split("?")[0];
      if (sId && sId !== "categories" && sId !== "browse" && sId !== "saved" && sId !== "applications") {
        return { type: "scheme_detail", schemeId: decodeURIComponent(sId) };
      }
    }
    return { type: "categories" };
  });

  const { user, activeBeneficiary: authActiveBeneficiary } = useCitizenAuth();

  // Data States
  const [categories, setCategories] = useState<SchemeCategoryDTO[]>([]);
  const [categorySchemes, setCategorySchemes] = useState<SchemeListItemDTO[]>([]);
  const [categoryTotal, setCategoryTotal] = useState<number>(0);
  const [activeCategory, setActiveCategory] = useState<SchemeCategoryDTO | null>(null);
  
  const [selectedSchemeDetail, setSelectedSchemeDetail] = useState<SchemeDetailDTO | null>(null);
  const [applicationGuidance, setApplicationGuidance] = useState<SchemeApplicationGuidanceDTO | null>(null);
  const [savedSchemes, setSavedSchemes] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [helpCentres, setHelpCentres] = useState<SchemeHelpCentreItemDTO[]>([]);
  const [helpRequirements, setHelpRequirements] = useState<SchemeHelpRequirementsDTO | null>(null);
  const [selectedFacilityDetail, setSelectedFacilityDetail] = useState<SchemeFacilityDetailDTO | null>(null);
  const [householdMembers, setHouseholdMembers] = useState<any[]>([]);
  const [homeSummary, setHomeSummary] = useState<any>(null);

  // Help Centres Location & Filter States
  const [locationSource, setLocationSource] = useState<"CURRENT_GPS" | "REGISTERED_ADDRESS" | "MANUAL" | "MAP_SELECTED">("CURRENT_GPS");
  const [userCoordinates, setUserCoordinates] = useState<{ latitude: number; longitude: number; source?: string } | null>({ latitude: 18.5204, longitude: 73.8567, source: "DEVICE_GPS" });
  const [manualVillageOrPin, setManualVillageOrPin] = useState("");
  const [locationAddressDisplay, setLocationAddressDisplay] = useState("Kalyanpur (Current GPS)");
  const [searchRadiusKm, setSearchRadiusKm] = useState(50);
  const [isGpsLocating, setIsGpsLocating] = useState(false);
  const [showMapView, setShowMapView] = useState(false);

  // Category List Filter States
  const [searchQuery, setSearchQuery] = useState("");
  const [authorityFilter, setAuthorityFilter] = useState<"ALL" | "Central" | "Maharashtra">("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");

  // Single / Batch Eligibility States - dynamically bound to logged in citizen
  const [selectedBeneficiary, setSelectedBeneficiary] = useState<any>(() => ({
    type: "MYSELF",
    name: user?.name || "मी स्वतः (Self)",
    age: 28,
    gender: "FEMALE",
    state: "Maharashtra",
    district: "District 04",
    is_pregnant: true,
    gestational_weeks: 26,
    social_category: "BPL"
  }));
  const [singleSchemeEligibility, setSingleSchemeEligibility] = useState<any>(null);
  const [missingFactsInput, setMissingFactsInput] = useState<Record<string, any>>({});
  const [allScreeningResults, setAllScreeningResults] = useState<any[]>([]);
  const [activeScreeningId, setActiveScreeningId] = useState<string | null>(null);

  // Status & Feedback
  const [loading, setLoading] = useState(false);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  // Keep selectedBeneficiary in sync with logged in user or auth active beneficiary
  useEffect(() => {
    if (user?.name) {
      setSelectedBeneficiary((prev: any) => {
        if (prev.type === "MYSELF") {
          return {
            ...prev,
            name: user.name,
            village_name: user.village_name || prev.village_name
          };
        }
        return prev;
      });
    }
  }, [user]);

  // Navigation Sync Helper
  const navigateTo = useCallback((route: SchemeRoute, replace = false) => {
    setRouteState(route);
    setErrorMsg(null);
    let url = "/citizen/schemes";
    if (route.type === "category_list") {
      url = `/citizen/schemes/category/${encodeURIComponent(route.categoryId)}`;
    } else if (route.type === "scheme_detail") {
      url = `/citizen/schemes/${encodeURIComponent(route.schemeId)}`;
    } else if (route.type === "eligibility") {
      url = `/citizen/schemes/${encodeURIComponent(route.schemeId)}/eligibility`;
    } else if (route.type === "how_to_apply") {
      url = `/citizen/schemes/${encodeURIComponent(route.schemeId)}/how-to-apply`;
    } else if (route.type === "help_centres") {
      url = `/citizen/schemes/${encodeURIComponent(route.schemeId)}/help-centres`;
    } else if (route.type === "help_centre_detail") {
      url = `/citizen/schemes/${encodeURIComponent(route.schemeId)}/help-centres/${encodeURIComponent(route.facilityId)}`;
    }
    if (replace) {
      window.history.replaceState({ route }, "", url);
    } else {
      window.history.pushState({ route }, "", url);
    }
  }, []);

  // Listen for browser Back/Forward buttons
  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      if (e.state?.route) {
        setRouteState(e.state.route);
      } else {
        const path = window.location.pathname;
        if (path.includes("/citizen/schemes/category/")) {
          const catId = path.split("/citizen/schemes/category/")[1]?.split("/")[0];
          if (catId) setRouteState({ type: "category_list", categoryId: decodeURIComponent(catId) });
        } else if (path.includes("/help-centres/")) {
          const parts = path.split("/citizen/schemes/")[1]?.split("/help-centres/");
          if (parts && parts[0] && parts[1]) {
            setRouteState({ type: "help_centre_detail", schemeId: decodeURIComponent(parts[0]), facilityId: decodeURIComponent(parts[1]) });
          }
        } else if (path.includes("/help-centres")) {
          const match = path.match(/\/citizen\/schemes\/([^/]+)\/help-centres/);
          if (match && match[1]) setRouteState({ type: "help_centres", schemeId: decodeURIComponent(match[1]) });
        } else if (path.includes("/eligibility")) {
          const match = path.match(/\/citizen\/schemes\/([^/]+)\/eligibility/);
          if (match && match[1]) setRouteState({ type: "eligibility", schemeId: decodeURIComponent(match[1]) });
        } else if (path.includes("/how-to-apply")) {
          const match = path.match(/\/citizen\/schemes\/([^/]+)\/how-to-apply/);
          if (match && match[1]) setRouteState({ type: "how_to_apply", schemeId: decodeURIComponent(match[1]) });
        } else if (path.startsWith("/citizen/schemes/")) {
          const sId = path.replace("/citizen/schemes/", "").split("/")[0];
          if (sId && sId !== "categories" && sId !== "saved") {
            setRouteState({ type: "scheme_detail", schemeId: decodeURIComponent(sId) });
          } else {
            setRouteState({ type: "categories" });
          }
        } else {
          setRouteState({ type: "categories" });
        }
      }
    };

    const handleOnlineStatus = () => setIsOffline(!navigator.onLine);
    window.addEventListener("popstate", handlePopState);
    window.addEventListener("online", handleOnlineStatus);
    window.addEventListener("offline", handleOnlineStatus);

    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("online", handleOnlineStatus);
      window.removeEventListener("offline", handleOnlineStatus);
    };
  }, []);

  // TTS Read Aloud Helper
  const speakText = (text: string) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const lang = locale || "mr-IN";
    utterance.lang = lang.startsWith("hi") ? "hi-IN" : (lang.startsWith("en") ? "en-IN" : "mr-IN");
    utterance.rate = 0.9;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  // 1. Load Initial Categories & Data with Offline Fallback Cache
  const loadInitialData = async () => {
    setLoading(true);
    setCategoriesLoading(true);
    setCategoriesError(null);
    setErrorMsg(null);
    try {
      const [catRes, homeRes, savedRes, appRes, centresRes, householdRes] = await Promise.allSettled([
        apiClient.getCitizenSchemeCategories(),
        apiClient.getCitizenSchemesHome(),
        apiClient.getSavedCitizenSchemes(),
        apiClient.getCitizenSchemeApplications(),
        apiClient.getCitizenSchemeHelpCentres(),
        apiClient.getHouseholdMembers()
      ]);

      if (catRes.status === "fulfilled") {
        const catData = catRes.value?.data || catRes.value || [];
        setCategories(catData);
        setCategoriesError(null);
        try { localStorage.setItem("aarogya_cached_categories", JSON.stringify(catData)); } catch (e) {}
      } else {
        const cached = localStorage.getItem("aarogya_cached_categories");
        if (cached) {
          setCategories(JSON.parse(cached));
        } else {
          setCategoriesError("योजना वर्गवारी लोड करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.");
        }
      }

      if (homeRes.status === "fulfilled") setHomeSummary(homeRes.value?.data || homeRes.value);
      if (savedRes.status === "fulfilled") {
        const savedData = savedRes.value?.data || savedRes.value || [];
        setSavedSchemes(savedData);
        try { localStorage.setItem("aarogya_cached_saved_schemes", JSON.stringify(savedData)); } catch (e) {}
      }
      if (appRes.status === "fulfilled") setApplications(appRes.value?.data || appRes.value || []);
      if (centresRes.status === "fulfilled") {
        const raw = centresRes.value?.data?.items || centresRes.value?.data || centresRes.value || [];
        setHelpCentres(Array.isArray(raw) ? raw : (raw.items || []));
      }
      if (householdRes.status === "fulfilled") {
        const rawH = householdRes.value?.data?.items || householdRes.value?.data || householdRes.value || [];
        setHouseholdMembers(Array.isArray(rawH) ? rawH : []);
      }
    } catch (err: any) {
      console.error("Failed to load schemes initial data", err);
      setErrorMsg("माहिती लोड करण्यात अडचण आली. कृपया पुन्हा प्रयत्न करा.");
      setCategoriesError("योजना माहिती लोड करता आली नाही.");
    } finally {
      setLoading(false);
      setCategoriesLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // 2. Fetch Schemes when route is category_list
  useEffect(() => {
    if (routeState.type === "category_list") {
      const fetchCategorySchemes = async () => {
        setLoading(true);
        setErrorMsg(null);
        try {
          const res = await apiClient.getCitizenSchemes({
            category_id: routeState.categoryId,
            state: authorityFilter === "Maharashtra" ? "Maharashtra" : undefined,
            query: searchQuery || undefined,
            status: "ACTIVE"
          });
          const payload = res?.data || res || {};
          const items = payload.items || payload || [];
          setCategorySchemes(items);
          setCategoryTotal(payload.total || items.length);

          const matchedCat = categories.find(c => c.category_id === routeState.categoryId || c.category_code === routeState.categoryId);
          if (matchedCat) setActiveCategory(matchedCat);
        } catch (err: any) {
          console.error("Failed to fetch schemes for category", err);
          setErrorMsg("या वर्गवारीतील योजना लोड करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.");
        } finally {
          setLoading(false);
        }
      };
      fetchCategorySchemes();
    }
  }, [routeState, authorityFilter, searchQuery, categories]);

  // 3. Fetch Detail when route is scheme_detail, eligibility, how_to_apply, help_centres, or help_centre_detail
  useEffect(() => {
    if (
      routeState.type === "scheme_detail" ||
      routeState.type === "eligibility" ||
      routeState.type === "how_to_apply" ||
      routeState.type === "help_centres" ||
      routeState.type === "help_centre_detail"
    ) {
      const sId = (routeState as any).schemeId;
      if (!sId) return;

      const fetchDetail = async () => {
        setLoading(true);
        setErrorMsg(null);
        try {
          const [detailRes, guidanceRes, reqRes] = await Promise.allSettled([
            apiClient.getCitizenSchemeDetail(sId),
            apiClient.getCitizenSchemeApplicationGuidance(sId),
            apiClient.getCitizenSchemeHelpRequirements(sId)
          ]);

          if (detailRes.status === "fulfilled") {
            const detailData = detailRes.value?.data || detailRes.value;
            setSelectedSchemeDetail(detailData);
          } else {
            setErrorMsg("योजना सापडली नाही (Scheme not found 404).");
          }

          if (guidanceRes.status === "fulfilled") {
            setApplicationGuidance(guidanceRes.value?.data || guidanceRes.value);
          }

          if (reqRes.status === "fulfilled") {
            setHelpRequirements(reqRes.value?.data || reqRes.value);
          }
        } catch (err: any) {
          console.error("Failed to load scheme detail", err);
          setErrorMsg("योजनेची माहिती लोड करताना अडचण आली.");
        } finally {
          setLoading(false);
        }
      };
      fetchDetail();
    }
  }, [routeState]);

  // 3b. Fetch Help Centres when in help_centres view
  const fetchSchemeHelpCentres = useCallback(async (
    schemeId: string,
    coords = userCoordinates,
    radius = searchRadiusKm,
    manualLoc = manualVillageOrPin
  ) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await apiClient.searchCitizenSchemeHelpCentres(schemeId, {
        scheme_version_id: selectedSchemeDetail?.scheme_version || undefined,
        beneficiary_id: selectedBeneficiary?.id,
        location: {
          source: locationSource,
          latitude: coords?.latitude || 18.5204,
          longitude: coords?.longitude || 73.8567,
          village: manualLoc && isNaN(Number(manualLoc)) ? manualLoc : undefined,
          pincode: manualLoc && !isNaN(Number(manualLoc)) ? manualLoc : undefined,
          accuracy_m: 30,
          captured_at: new Date().toISOString()
        },
        radius_km: radius,
        language: locale || "mr-IN"
      });
      const data = res?.data || res || {};
      setHelpCentres(data.items || []);
    } catch (err: any) {
      console.error("Failed to search scheme help centres", err);
      setErrorMsg("मदत केंद्र शोधताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.");
    } finally {
      setLoading(false);
    }
  }, [selectedSchemeDetail, selectedBeneficiary, locationSource, userCoordinates, searchRadiusKm, manualVillageOrPin, locale]);

  useEffect(() => {
    if (routeState.type === "help_centres") {
      fetchSchemeHelpCentres(routeState.schemeId);
    }
  }, [routeState, fetchSchemeHelpCentres]);

  // 3c. Fetch Specific Facility Detail when in help_centre_detail view
  useEffect(() => {
    if (routeState.type === "help_centre_detail") {
      const fetchFacDetail = async () => {
        setLoading(true);
        setErrorMsg(null);
        try {
          const res = await apiClient.getCitizenSchemeHelpCentreDetail(
            routeState.schemeId,
            routeState.facilityId,
            {
              language: locale || "mr-IN",
              lat: userCoordinates?.latitude,
              lon: userCoordinates?.longitude
            }
          );
          setSelectedFacilityDetail(res?.data || res);
        } catch (err: any) {
          console.error("Failed to fetch facility detail", err);
          setErrorMsg("मदत केंद्राचा तपशील लोड करता आला नाही (404).");
        } finally {
          setLoading(false);
        }
      };
      fetchFacDetail();
    }
  }, [routeState, locale, userCoordinates]);


  // 4. Run Single Scheme Eligibility Check
  const runSingleEligibilityCheck = async (schemeId: string, beneficiary = selectedBeneficiary, additionalFacts = missingFactsInput) => {
    if (!navigator.onLine) {
      setErrorMsg("Eligibility check requires connection. (पात्रता तपासणीसाठी इंटरनेट आवश्यक आहे)");
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const payload = {
        household_member_id: beneficiary?.id,
        is_pregnant: beneficiary?.is_pregnant,
        age: beneficiary?.age || beneficiary?.age_estimate,
        additional_facts: {
          ...beneficiary,
          ...additionalFacts
        }
      };
      const res = await apiClient.screenCitizenSchemeSingle(schemeId, payload);
      const data = res?.data || res;
      setSingleSchemeEligibility(data);
    } catch (err: any) {
      console.error("Single eligibility screening failed", err);
      setErrorMsg("पात्रता तपासणी अयशस्वी झाली. कृपया नेटवर्क तपासा.");
    } finally {
      setLoading(false);
    }
  };

  // 5. Run Full Screening for all schemes
  const runFullScreening = async (beneficiary = selectedBeneficiary, factsOverride = {}) => {
    if (!navigator.onLine) {
      setErrorMsg("Eligibility check requires connection.");
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const payload = {
        household_member_id: beneficiary?.id,
        is_pregnant: beneficiary?.is_pregnant,
        age: beneficiary?.age || beneficiary?.age_estimate,
        additional_facts: {
          ...beneficiary,
          ...factsOverride
        }
      };
      const res = await apiClient.screenCitizenSchemes(payload);
      const data = res?.data || res;
      setActiveScreeningId(data.screening_id);
      setAllScreeningResults(data.results || []);
      navigateTo({ type: "all_screening_results" });
    } catch (err: any) {
      console.error("Batch screening failed", err);
      setErrorMsg("पात्रता तपासणी अयशस्वी झाली.");
    } finally {
      setLoading(false);
    }
  };

  // 6. Bookmark / Toggle Save Scheme
  const toggleSaveScheme = async (schemeCode: string, schemeName: string) => {
    const isSaved = savedSchemes.some(s => s.scheme_code === schemeCode || s.scheme_id === schemeCode);
    try {
      if (isSaved) {
        await apiClient.unsaveCitizenScheme(schemeCode);
        setSavedSchemes(prev => prev.filter(s => s.scheme_code !== schemeCode && s.scheme_id !== schemeCode));
        setActionSuccessMsg("योजना जतन केलेल्या यादीतून काढली.");
      } else {
        await apiClient.saveCitizenScheme(schemeCode);
        setSavedSchemes(prev => [...prev, { scheme_code: schemeCode, scheme_name: schemeName }]);
        setActionSuccessMsg("योजना यशस्वीपणे जतन केली (Saved)!");
      }
      setTimeout(() => setActionSuccessMsg(null), 3000);
    } catch (err) {
      console.error("Failed to toggle save", err);
    }
  };

  // 7. Request ASHA Assistance for a scheme
  const handleRequestAshaAssistance = async (scheme: any) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const sCode = scheme.scheme_code || scheme.scheme_id;
      const res = await apiClient.requestSchemeAshaAssistance(sCode, {
        household_member_id: selectedBeneficiary?.id,
        beneficiary_name: selectedBeneficiary?.name || selectedBeneficiary?.full_name || "Sunita Devi",
        screening_id: activeScreeningId,
        current_screening_status: scheme.eligibility_status || scheme.status || "MORE_INFORMATION_REQUIRED",
        missing_facts: scheme.missing_fields || [],
        missing_documents: scheme.required_documents || ["Aadhaar", "Ration Card"],
        preferred_contact_method: "HOME_VISIT"
      });
      setActionSuccessMsg(t("schemes.asha_help_requested_success", "आशा ताईंना सहाय्य विनंती पाठवली आहे!"));
      const appRes = await apiClient.getCitizenSchemeApplications();
      setApplications(appRes?.data || appRes || []);
      setTimeout(() => {
        setActionSuccessMsg(null);
        navigateTo({ type: "applications" });
      }, 1200);
    } catch (err) {
      console.error("Failed to request ASHA assistance", err);
      setErrorMsg("आशा सहाय्य विनंती नोंदवताना त्रुटी आली.");
    } finally {
      setLoading(false);
    }
  };

  // Helper: Icons Mapper
  const renderCategoryIcon = (iconName: string) => {
    const props = { size: 24, color: "#1D4ED8" };
    switch (iconName) {
      case "Baby": return <Baby {...props} />;
      case "HeartHandshake": return <HeartHandshake {...props} />;
      case "ShieldCheck": return <ShieldCheck {...props} />;
      case "Pill": return <Pill {...props} />;
      case "Activity": return <Activity {...props} />;
      case "Stethoscope": return <Stethoscope {...props} />;
      case "UserCheck": return <User {...props} />;
      case "Accessibility": return <Accessibility {...props} />;
      case "IndianRupee": return <IndianRupee {...props} />;
      case "Smile": return <Smile {...props} />;
      case "Heart": return <Heart {...props} />;
      default: return <Building2 {...props} />;
    }
  };

  // Helper: Status Badges with deterministic colors
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "LIKELY_ELIGIBLE":
      case "POTENTIALLY_ELIGIBLE":
        return {
          bg: "#DCFCE7",
          color: "#15803D",
          border: "#86EFAC",
          label: locale === "en-IN" ? "Likely Eligible" : (locale === "hi-IN" ? "पात्र होने की संभावना" : "पात्र असण्याची शक्यता")
        };
      case "SERVICE_AVAILABLE":
      case "SERVICE_RELEVANT":
        return {
          bg: "#E0F2FE",
          color: "#0369A1",
          border: "#7DD3FC",
          label: locale === "en-IN" ? "Service Available" : (locale === "hi-IN" ? "मुफ्त सेवा उपलब्ध" : "मोफत सेवा उपलब्ध")
        };
      case "OFFICIAL_VERIFICATION_REQUIRED":
        return {
          bg: "#FEF3C7",
          color: "#B45309",
          border: "#FDE68A",
          label: locale === "en-IN" ? "Official Verification Required" : (locale === "hi-IN" ? "शासकीय सत्यापन आवश्यक" : "शासकीय पडताळणी आवश्यक")
        };
      case "MORE_INFORMATION_REQUIRED":
      default:
        return {
          bg: "#F1F5F9",
          color: "#475569",
          border: "#CBD5E1",
          label: locale === "en-IN" ? "More Information Required" : (locale === "hi-IN" ? "अधिक जानकारी आवश्यक" : "अधिक माहिती हवी")
        };
    }
  };

  // Category Translation Helper
  const getCategoryTitle = (cat: SchemeCategoryDTO) => {
    if (locale === "en-IN") return cat.title_en || cat.translated_name;
    if (locale === "hi-IN") return cat.title_hi || cat.translated_name;
    return cat.title_mr || cat.translated_name;
  };

  const getCategoryDesc = (cat: SchemeCategoryDTO) => {
    if (locale === "en-IN") return cat.title_en;
    return cat.translated_description || cat.title_mr || "";
  };

  const getPlanCountText = (count: number) => {
    if (locale === "en-IN") {
      return count === 1 ? "1 plan" : `${count} plans`;
    }
    if (locale === "hi-IN") {
      return count === 1 ? "1 योजना" : `${count} योजनाएं`;
    }
    return `${count} योजना`;
  };

  // ==========================================
  // VIEW 1: CATEGORIES GRID (/citizen/schemes)
  // ==========================================
  const renderCategoriesView = () => {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header with Title & Read Aloud */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: "0 0 4px 0" }}>
              {t("schemes.title", "सरकारी आरोग्य योजना")}
            </h1>
            <div style={{ fontSize: 13, color: "#64748B", fontWeight: 600 }}>
              {t("schemes.subtitle", "Government Health Benefits & Assistance")}
            </div>
          </div>
          <button
            onClick={() => speakText("सरकारी आरोग्य योजना. आपल्यासाठी आणि कुटुंबासाठी मोफत आरोग्य योजना व रोख मदत शोधा.")}
            style={{
              backgroundColor: isSpeaking ? "#DCFCE7" : "#F1F5F9",
              border: "1px solid #CBD5E1",
              padding: "8px 12px",
              borderRadius: 12,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 12,
              fontWeight: 700,
              color: isSpeaking ? "#15803D" : "#334155",
              minHeight: 48
            }}
          >
            <Volume2 size={18} /> {t("common.read_aloud", "ऐका")}
          </button>
        </div>

        {/* Offline Banner */}
        {isOffline && (
          <div style={{ backgroundColor: "#FEF2F2", border: "1.5px solid #FCA5A5", borderRadius: 12, padding: "10px 14px", display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#991B1B", fontWeight: 700 }}>
            <AlertTriangle size={18} color="#991B1B" />
            <span>{t("schemes.offline_notice", "Eligibility check requires connection.")}</span>
          </div>
        )}

        {/* Action Check for Myself / Family */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <button
            id="btn-check-for-me"
            onClick={() => {
              const selfBeneficiary = {
                type: "MYSELF",
                name: user?.name || "मी स्वतः (Self)",
                age: 28,
                gender: "FEMALE",
                state: "Maharashtra",
                district: "District 04",
                is_pregnant: true,
                gestational_weeks: 26,
                social_category: "BPL"
              };
              setSelectedBeneficiary(selfBeneficiary);
              runFullScreening(selfBeneficiary);
            }}
            style={{
              backgroundColor: "#1D4ED8",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 16,
              padding: "16px 12px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              cursor: "pointer",
              boxShadow: "0 4px 12px rgba(29, 78, 216, 0.2)",
              minHeight: 48
            }}
          >
            <User size={26} />
            <span style={{ fontSize: 13, fontWeight: 800, textAlign: "center" }}>
              {t("schemes.screen_for_myself", "माझ्यासाठी पात्रता तपासा")}<br />
              <span style={{ fontSize: 10, fontWeight: 500, opacity: 0.9 }}>(Check for Me)</span>
            </span>
          </button>

          <button
            id="btn-check-for-family"
            onClick={() => navigateTo({ type: "check_beneficiary" })}
            style={{
              backgroundColor: "#FFFFFF",
              color: "#1E293B",
              border: "2px solid #E2E8F0",
              borderRadius: 16,
              padding: "16px 12px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              cursor: "pointer",
              minHeight: 48
            }}
          >
            <Users size={26} color="#1D4ED8" />
            <span style={{ fontSize: 13, fontWeight: 800, textAlign: "center" }}>
              {t("schemes.screen_for_family", "कुटुंबासाठी तपासा")}<br />
              <span style={{ fontSize: 10, fontWeight: 500, color: "#64748B" }}>(Family Member)</span>
            </span>
          </button>
        </div>

        {/* Quick Nav Tags */}
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 4 }}>
          <button
            id="btn-nav-saved"
            onClick={() => navigateTo({ type: "saved_schemes" })}
            style={{
              backgroundColor: "#F8FAFC",
              border: "1px solid #CBD5E1",
              borderRadius: 20,
              padding: "8px 14px",
              fontSize: 12,
              fontWeight: 700,
              color: "#334155",
              whiteSpace: "nowrap",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              minHeight: 40
            }}
          >
            <Bookmark size={14} /> {t("schemes.saved_scheme", "जतन केलेल्या")} ({savedSchemes.length})
          </button>

          <button
            id="btn-nav-applications"
            onClick={() => navigateTo({ type: "applications" })}
            style={{
              backgroundColor: "#F8FAFC",
              border: "1px solid #CBD5E1",
              borderRadius: 20,
              padding: "8px 14px",
              fontSize: 12,
              fontWeight: 700,
              color: "#334155",
              whiteSpace: "nowrap",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              minHeight: 40
            }}
          >
            <Award size={14} /> माझे अर्ज ({applications.length})
          </button>

          <button
            id="btn-nav-help-centres"
            onClick={() => navigateTo({ type: "help_centres", schemeId: selectedSchemeDetail?.scheme_id || selectedSchemeDetail?.scheme_code || "ALL" })}
            style={{
              backgroundColor: "#F8FAFC",
              border: "1px solid #CBD5E1",
              borderRadius: 20,
              padding: "8px 14px",
              fontSize: 12,
              fontWeight: 700,
              color: "#334155",
              whiteSpace: "nowrap",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              minHeight: 40
            }}
          >
            <Building2 size={14} /> {t("schemes.find_help_centre", "मदत केंद्र")}
          </button>
        </div>

        {/* 12 Interactive Accessible Category Buttons */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ fontSize: 16, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("schemes.categories_title", "आरोग्य वर्गवारीनुसार योजना (Categories)")}
            </h2>
          </div>

          {categoriesLoading ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  style={{
                    backgroundColor: "#FFFFFF",
                    border: "1.5px solid #E2E8F0",
                    borderRadius: 16,
                    padding: "16px 14px",
                    minHeight: 120,
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                    animation: "pulse 1.5s infinite"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ width: 44, height: 44, borderRadius: 12, backgroundColor: "#F1F5F9" }} />
                    <div style={{ width: 50, height: 20, borderRadius: 10, backgroundColor: "#F1F5F9" }} />
                  </div>
                  <div style={{ width: "70%", height: 16, backgroundColor: "#F1F5F9", borderRadius: 4, marginTop: 4 }} />
                  <div style={{ width: "90%", height: 12, backgroundColor: "#F1F5F9", borderRadius: 4 }} />
                </div>
              ))}
            </div>
          ) : categoriesError ? (
            <div style={{ textAlign: "center", padding: "32px 16px", backgroundColor: "#FEF2F2", borderRadius: 16, border: "1.5px solid #FCA5A5" }}>
              <AlertCircle size={36} color="#DC2626" style={{ margin: "0 auto 8px auto" }} />
              <div style={{ fontSize: 14, fontWeight: 800, color: "#991B1B" }}>
                {categoriesError}
              </div>
              <button
                id="btn-retry-categories"
                onClick={() => loadInitialData()}
                style={{
                  marginTop: 12,
                  backgroundColor: "#DC2626",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: 10,
                  padding: "8px 16px",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  minHeight: 40
                }}
              >
                <RefreshCw size={14} /> {t("common.retry", "पुन्हा प्रयत्न करा")}
              </button>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {categories.map((cat) => {
                const count = cat.active_scheme_count ?? cat.count ?? 0;
                const countLabel = getPlanCountText(count);

                return (
                  <button
                    key={cat.category_id || cat.category_code}
                    id={`scheme-category-card-${cat.category_id || cat.category_code}`}
                    onClick={() => {
                      setActiveCategory(cat);
                      navigateTo({ type: "category_list", categoryId: cat.category_id || cat.category_code });
                    }}
                    style={{
                      backgroundColor: "#FFFFFF",
                      border: "1.5px solid #E2E8F0",
                      borderRadius: 16,
                      padding: "16px 14px",
                      display: "flex",
                      flexDirection: "column",
                      gap: 10,
                      cursor: "pointer",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.03)",
                      textAlign: "left",
                      minHeight: 120,
                      width: "100%",
                      outline: "none",
                      transition: "all 0.15s ease"
                    }}
                    onFocus={(e) => (e.currentTarget.style.borderColor = "#1D4ED8")}
                    onBlur={(e) => (e.currentTarget.style.borderColor = "#E2E8F0")}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 12,
                          backgroundColor: "#EFF6FF",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                      >
                        {renderCategoryIcon(cat.icon)}
                      </div>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 800,
                          color: "#1D4ED8",
                          backgroundColor: "#DBEAFE",
                          padding: "3px 8px",
                          borderRadius: 10
                        }}
                      >
                        {countLabel}
                      </span>
                    </div>

                    <div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: "#0F172A", lineHeight: 1.3 }}>
                        {getCategoryTitle(cat)}
                      </div>
                      <div style={{ fontSize: 11, color: "#64748B", marginTop: 4, lineHeight: 1.35 }}>
                        {getCategoryDesc(cat)}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  };

  // =========================================================================
  // VIEW 2: CATEGORY FILTERED SCHEME LIST (/citizen/schemes/category/:catId)
  // =========================================================================
  const renderCategoryListView = (categoryId: string) => {
    const cat = activeCategory || categories.find(c => c.category_id === categoryId || c.category_code === categoryId);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Header & Back */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            id='btn-back-to-categories'
            onClick={() => navigateTo({ type: 'categories' })}
            style={{ border: 'none', background: '#F1F5F9', padding: '10px 14px', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 700, minHeight: 48 }}
          >
            <ArrowLeft size={18} color='#1E293B' /> {t('common.back', 'मागे')}
          </button>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#64748B' }}>
            {categoryTotal} {t('schemes.plans_available', 'योजना उपलब्ध')}
          </span>
        </div>

        {/* Category Header Card */}
        <div style={{ backgroundColor: '#EFF6FF', border: '1.5px solid #BFDBFE', borderRadius: 18, padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: '#DBEAFE', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {cat && renderCategoryIcon(cat.icon)}
            </div>
            <div>
              <h2 style={{ fontSize: 17, fontWeight: 800, color: '#1E40AF', margin: 0 }}>
                {cat?.translated_name || cat?.title_mr || categoryId}
              </h2>
              <div style={{ fontSize: 11, color: '#3B82F6', fontWeight: 600 }}>
                {cat?.translated_description || 'Government Health Support & Services'}
              </div>
            </div>
          </div>
        </div>

        {/* Search & Authority Filter */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} color='#94A3B8' style={{ position: 'absolute', left: 14, top: 16 }} />
            <input
              type='text'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('schemes.search_in_category', 'या वर्गवारीत शोधा...')}
              style={{
                width: '100%',
                padding: '12px 14px 12px 38px',
                borderRadius: 14,
                border: '1.5px solid #CBD5E1',
                fontSize: 13,
                outline: 'none',
                minHeight: 48,
                backgroundColor: '#FFFFFF'
              }}
            />
          </div>

          {/* Central / Maharashtra Authority Filter */}
          <div style={{ display: 'flex', gap: 8 }}>
            {(['ALL', 'Central', 'Maharashtra'] as const).map((auth) => (
              <button
                key={auth}
                id={`filter-auth-${auth.toLowerCase()}`}
                onClick={() => setAuthorityFilter(auth)}
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  borderRadius: 10,
                  fontSize: 12,
                  fontWeight: 700,
                  border: authorityFilter === auth ? '2px solid #1D4ED8' : '1px solid #E2E8F0',
                  backgroundColor: authorityFilter === auth ? '#DBEAFE' : '#FFFFFF',
                  color: authorityFilter === auth ? '#1D4ED8' : '#475569',
                  cursor: 'pointer',
                  minHeight: 42
                }}
              >
                {auth === 'ALL' ? t('schemes.filter_all', 'सर्व (All)') : (auth === 'Central' ? 'केंद्र शासन' : 'महाराष्ट्र')}
              </button>
            ))}
          </div>
        </div>

        {/* Schemes List / Skeleton / Empty State */}
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[1, 2, 3].map(i => (
              <div key={i} style={{ backgroundColor: '#F1F5F9', height: 110, borderRadius: 16, animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : errorMsg ? (
          <div style={{ textAlign: 'center', padding: '32px 16px', backgroundColor: '#FEF2F2', borderRadius: 16, border: '1.5px solid #FCA5A5' }}>
            <AlertCircle size={36} color="#DC2626" style={{ margin: '0 auto 8px auto' }} />
            <div style={{ fontSize: 14, fontWeight: 800, color: '#991B1B' }}>
              {errorMsg}
            </div>
            <button
              onClick={() => {
                setLoading(true);
                setErrorMsg(null);
                apiClient.getCitizenSchemes({
                  category_id: (routeState as any).categoryId,
                  state: authorityFilter === "Maharashtra" ? "Maharashtra" : undefined,
                  query: searchQuery || undefined,
                  status: "ACTIVE"
                }).then((res: any) => {
                  const payload = res?.data || res || {};
                  const items = payload.items || payload || [];
                  setCategorySchemes(items);
                  setCategoryTotal(payload.total || items.length);
                }).catch((err: any) => {
                  setErrorMsg("या वर्गवारीतील योजना लोड करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.");
                }).finally(() => setLoading(false));
              }}
              style={{
                marginTop: 12,
                backgroundColor: '#DC2626',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: 10,
                padding: '8px 16px',
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                minHeight: 40
              }}
            >
              <RefreshCw size={14} /> {t('common.retry', 'पुन्हा प्रयत्न करा')}
            </button>
          </div>
        ) : categorySchemes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 16px', backgroundColor: '#F8FAFC', borderRadius: 16, border: '1px dashed #CBD5E1' }}>
            <Award size={40} color='#94A3B8' style={{ margin: '0 auto 10px auto' }} />
            <div style={{ fontSize: 15, fontWeight: 700, color: '#334155' }}>
              {t('schemes.no_schemes_found', 'कोणतीही योजना आढळली नाही.')}
            </div>
            <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
              फिल्टर बदलून पहा किंवा सर्व योजना तपासा.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {categorySchemes.map((s) => {
              const isSaved = savedSchemes.some(saved => saved.scheme_code === s.scheme_code || saved.scheme_id === s.scheme_id);

              return (
                <div
                  key={s.scheme_id || s.scheme_code}
                  id={`scheme-item-${s.scheme_code}`}
                  style={{
                    backgroundColor: '#FFFFFF',
                    border: '1.5px solid #E2E8F0',
                    borderRadius: 18,
                    padding: '16px',
                    boxShadow: '0 3px 10px rgba(0,0,0,0.03)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
                        <span style={{ fontSize: 10, fontWeight: 800, backgroundColor: '#EFF6FF', color: '#1D4ED8', padding: '2px 8px', borderRadius: 6 }}>
                          {s.classification || 'PUBLIC HEALTH SCHEME'}
                        </span>
                        <span style={{ fontSize: 10, fontWeight: 700, backgroundColor: '#F1F5F9', color: '#475569', padding: '2px 8px', borderRadius: 6 }}>
                          {s.government_level} • {s.applicable_state}
                        </span>
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 800, color: '#0F172A', margin: '4px 0' }}>
                        {s.scheme_name || s.canonical_name}
                      </h3>
                      <div style={{ fontSize: 11, color: '#64748B' }}>
                        प्राधिकरण: {s.authority_name} • पडताळणी: {s.last_verified_date}
                      </div>
                    </div>

                    <button
                      onClick={() => toggleSaveScheme(s.scheme_code, s.scheme_name)}
                      style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 6, minHeight: 40 }}
                      aria-label='Save Scheme'
                    >
                      {isSaved ? <BookmarkCheck size={22} color='#1D4ED8' /> : <Bookmark size={22} color='#94A3B8' />}
                    </button>
                  </div>

                  <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.45, backgroundColor: '#F8FAFC', padding: '10px', borderRadius: 10 }}>
                    <strong>लाभ / सेवा:</strong> {s.benefit_one_liner || s.description?.slice(0, 110)}...
                  </div>

                  {/* 4 Action Buttons */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 4 }}>
                    <button
                      id={`btn-details-${s.scheme_code}`}
                      onClick={() => navigateTo({ type: 'scheme_detail', schemeId: s.scheme_id || s.scheme_code })}
                      style={{
                        backgroundColor: '#1D4ED8',
                        color: '#FFFFFF',
                        border: 'none',
                        borderRadius: 10,
                        padding: '10px',
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: 'pointer',
                        minHeight: 48
                      }}
                    >
                      {t('schemes.view_details', 'सविस्तर माहिती')}
                    </button>

                    <button
                      id={`btn-eligibility-${s.scheme_code}`}
                      onClick={() => {
                        setSelectedSchemeDetail(s as any);
                        runSingleEligibilityCheck(s.scheme_code);
                        navigateTo({ type: 'eligibility', schemeId: s.scheme_code });
                      }}
                      style={{
                        backgroundColor: '#EFF6FF',
                        color: '#1D4ED8',
                        border: '1.5px solid #BFDBFE',
                        borderRadius: 10,
                        padding: '10px',
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: 'pointer',
                        minHeight: 48
                      }}
                    >
                      {t('schemes.check_eligibility', 'पात्रता तपासा')}
                    </button>

                    <button
                      id={`btn-how-to-apply-${s.scheme_code}`}
                      onClick={() => navigateTo({ type: 'how_to_apply', schemeId: s.scheme_code })}
                      style={{
                        backgroundColor: '#F8FAFC',
                        color: '#334155',
                        border: '1px solid #CBD5E1',
                        borderRadius: 10,
                        padding: '10px',
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: 'pointer',
                        minHeight: 48
                      }}
                    >
                      {t('schemes.how_to_apply', 'अर्ज कसा करावा')}
                    </button>

                    {s.official_information_url ? (
                      <a
                        href={s.official_information_url}
                        target='_blank'
                        rel='noopener noreferrer'
                        style={{
                          backgroundColor: '#F8FAFC',
                          color: '#1D4ED8',
                          border: '1px solid #CBD5E1',
                          borderRadius: 10,
                          padding: '10px',
                          fontSize: 12,
                          fontWeight: 700,
                          textDecoration: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 4,
                          minHeight: 48
                        }}
                      >
                        अधिकृत स्रोत <ExternalLink size={14} />
                      </a>
                    ) : (
                      <button
                        onClick={() => handleRequestAshaAssistance(s)}
                        style={{
                          backgroundColor: '#FDF2F8',
                          color: '#BE185D',
                          border: '1px solid #FBCFE8',
                          borderRadius: 10,
                          padding: '10px',
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: 'pointer',
                          minHeight: 48
                        }}
                      >
                        आशा मदत घ्या
                      </button>
                    )}
                  </div>

                  <button
                    id={`btn-list-find-help-${s.scheme_code}`}
                    onClick={() => navigateTo({ type: 'help_centres', schemeId: s.scheme_id || s.scheme_code })}
                    style={{
                      backgroundColor: '#FFFFFF',
                      color: '#1E293B',
                      border: '1px solid #CBD5E1',
                      borderRadius: 10,
                      padding: '10px',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                      minHeight: 44
                    }}
                  >
                    <Building2 size={15} color='#1D4ED8' /> {t('schemes.find_help_centre', 'मदत केंद्र शोधा')}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  // =========================================================================
  // VIEW 3: SCHEME DETAIL (/citizen/schemes/:schemeId)
  // =========================================================================
  const renderSchemeDetailView = (schemeId: string) => {
    const s = selectedSchemeDetail;
    if (!s) {
      return (
        <div style={{ textAlign: 'center', padding: 40 }}>
          {errorMsg ? (
            <div>
              <div style={{ color: '#DC2626', fontWeight: 700, marginBottom: 12 }}>{errorMsg}</div>
              <button onClick={() => navigateTo({ type: 'categories' })} style={{ padding: '10px 16px', borderRadius: 10, backgroundColor: '#1D4ED8', color: '#FFF', border: 'none' }}>
                वर्गवारीकडे परत जा
              </button>
            </div>
          ) : (
            <div>माहिती लोड होत आहे...</div>
          )}
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Top Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            id='btn-back-to-category-list'
            onClick={() => {
              if (activeCategory) {
                navigateTo({ type: 'category_list', categoryId: activeCategory.category_id || activeCategory.category_code });
              } else {
                navigateTo({ type: 'categories' });
              }
            }}
            style={{ border: 'none', background: '#F1F5F9', padding: '10px 14px', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 700, minHeight: 48 }}
          >
            <ArrowLeft size={18} color='#1E293B' /> {t('common.back', 'मागे')}
          </button>

          <button
            onClick={() => toggleSaveScheme(s.scheme_code, s.scheme_name)}
            style={{ border: 'none', background: '#F1F5F9', padding: '10px 14px', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 700, minHeight: 48 }}
          >
            {savedSchemes.some(saved => saved.scheme_code === s.scheme_code || saved.scheme_id === s.scheme_id) ? (
              <><BookmarkCheck size={18} color='#1D4ED8' /> <span>{t('schemes.saved_scheme', 'जतन केली')}</span></>
            ) : (
              <><Bookmark size={18} color='#64748B' /> <span>{t('schemes.save_scheme', 'जतन करा')}</span></>
            )}
          </button>
        </div>

        {/* Scheme Header Card */}
        <div style={{ backgroundColor: '#EFF6FF', border: '1.5px solid #BFDBFE', borderRadius: 20, padding: '18px' }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 800, backgroundColor: '#DBEAFE', color: '#1E40AF', padding: '3px 8px', borderRadius: 6 }}>
              {s.classification || 'PUBLIC HEALTH SCHEME'}
            </span>
            <span style={{ fontSize: 11, fontWeight: 700, backgroundColor: '#FFFFFF', color: '#475569', padding: '3px 8px', borderRadius: 6, border: '1px solid #CBD5E1' }}>
              {s.government_level} • {(s.applicable_states && s.applicable_states.length > 0) ? s.applicable_states.join(", ") : "All India"}
            </span>
          </div>

          <h2 style={{ fontSize: 19, fontWeight: 800, color: '#0F172A', margin: '0 0 6px 0', lineHeight: 1.3 }}>
            {s.official_scheme_name || s.scheme_name}
          </h2>

          <div style={{ fontSize: 12, color: '#64748B', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>प्राधिकरण: <strong>{s.authority?.name || (s as any).authority_name}</strong></span>
            <span>•</span>
            <span>पडताळणी: {s.last_verified_date}</span>
          </div>
        </div>

        {/* Primary CTAs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <button
              id='btn-scheme-detail-eligibility'
              onClick={() => {
                runSingleEligibilityCheck(s.scheme_code);
                navigateTo({ type: 'eligibility', schemeId: s.scheme_code });
              }}
              style={{
                backgroundColor: '#1D4ED8',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: 14,
                padding: '14px',
                fontSize: 13,
                fontWeight: 800,
                cursor: 'pointer',
                minHeight: 48
              }}
            >
              {t('schemes.check_eligibility', 'पात्रता तपासा')}
            </button>

            <button
              id='btn-scheme-detail-how-to-apply'
              onClick={() => navigateTo({ type: 'how_to_apply', schemeId: s.scheme_code })}
              style={{
                backgroundColor: '#EFF6FF',
                color: '#1D4ED8',
                border: '1.5px solid #BFDBFE',
                borderRadius: 14,
                padding: '14px',
                fontSize: 13,
                fontWeight: 800,
                cursor: 'pointer',
                minHeight: 48
              }}
            >
              {t('schemes.how_to_apply', 'अर्ज कसा करावा')}
            </button>
          </div>

          <button
            id='btn-scheme-detail-find-help-centre'
            onClick={() => navigateTo({ type: 'help_centres', schemeId: s.scheme_id || s.scheme_code || schemeId })}
            style={{
              backgroundColor: '#FFFFFF',
              color: '#1E293B',
              border: '1.5px solid #CBD5E1',
              borderRadius: 14,
              padding: '14px',
              fontSize: 13,
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              minHeight: 48
            }}
          >
            <Building2 size={16} color='#1D4ED8' /> {t('schemes.find_help_centre', 'मदत केंद्र शोधा (Find Help Centre)')}
          </button>
        </div>
      </div>
    );
  };


const renderEligibilityView = (schemeId: string) => {
    const s = selectedSchemeDetail;
    const res = singleSchemeEligibility;
    const badge = getStatusBadge(res?.status || "MORE_INFORMATION_REQUIRED");

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Top Bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <button
            id="btn-back-to-scheme-detail"
            onClick={() => navigateTo({ type: "scheme_detail", schemeId })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 700, minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" /> {t("common.back", "मागे")}
          </button>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#1D4ED8" }}>
            नियम-आधारित पडताळणी (Rule Engine)
          </span>
        </div>

        {/* Beneficiary Selector (Myself / Household Member) */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 16, padding: "14px" }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B", marginBottom: 8 }}>
            लाभार्थी निवडा (Beneficiary):
          </div>
          <div style={{ display: "flex", gap: 8, overflowX: "auto" }}>
            <button
              id="beneficiary-myself"
              onClick={() => {
                const self = {
                  type: "MYSELF",
                  name: "Sunita Devi",
                  age: 24,
                  gender: "FEMALE",
                  state: "Maharashtra",
                  district: "District 04",
                  is_pregnant: true,
                  gestational_weeks: 26,
                  social_category: "BPL"
                };
                setSelectedBeneficiary(self);
                runSingleEligibilityCheck(schemeId, self);
              }}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                fontSize: 12,
                fontWeight: 700,
                border: selectedBeneficiary.type === "MYSELF" ? "2px solid #1D4ED8" : "1px solid #CBD5E1",
                backgroundColor: selectedBeneficiary.type === "MYSELF" ? "#DBEAFE" : "#FFFFFF",
                color: selectedBeneficiary.type === "MYSELF" ? "#1D4ED8" : "#334155",
                cursor: "pointer",
                minHeight: 40
              }}
            >
              👩 Sunita Devi (मी स्वतः)
            </button>

            {householdMembers.map((m) => (
              <button
                key={m.id}
                id={`beneficiary-member-${m.id}`}
                onClick={() => {
                  setSelectedBeneficiary(m);
                  runSingleEligibilityCheck(schemeId, m);
                }}
                style={{
                  padding: "8px 12px",
                  borderRadius: 10,
                  fontSize: 12,
                  fontWeight: 700,
                  border: selectedBeneficiary.id === m.id ? "2px solid #1D4ED8" : "1px solid #CBD5E1",
                  backgroundColor: selectedBeneficiary.id === m.id ? "#DBEAFE" : "#FFFFFF",
                  color: selectedBeneficiary.id === m.id ? "#1D4ED8" : "#334155",
                  cursor: "pointer",
                  minHeight: 40
                }}
              >
                👤 {m.full_name || m.name} ({m.relationship_type})
              </button>
            ))}
          </div>
        </div>

        {/* Screening Result Card */}
        {loading ? (
          <div style={{ padding: "30px", textAlign: "center", backgroundColor: "#F8FAFC", borderRadius: 16 }}>
            नियम तपासणी सुरू आहे... (Evaluating structured rules)
          </div>
        ) : res ? (
          <div style={{ backgroundColor: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: 18, padding: "16px", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
                  {res.scheme_name || s?.scheme_name}
                </h3>
                <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                  पडताळणी: 25 ऑगस्ट 2026 • 3-Valued Deterministic Rule Engine
                </div>
              </div>
            </div>

            <div
              style={{
                backgroundColor: badge.bg,
                color: badge.color,
                border: `1.5px solid ${badge.border}`,
                borderRadius: 10,
                padding: "8px 12px",
                fontSize: 13,
                fontWeight: 800,
                display: "inline-flex",
                alignItems: "center",
                gap: 6
              }}
            >
              <CheckCircle2 size={16} /> {badge.label}
            </div>

            {/* Matched Rules */}
            {res.matched_rules && res.matched_rules.length > 0 && (
              <div style={{ backgroundColor: "#F0FDF4", padding: "12px", borderRadius: 12, fontSize: 12, color: "#166534" }}>
                <div style={{ fontWeight: 800, marginBottom: 4 }}>
                  {t("schemes.matched_rules", "योजना का जुळली (पात्रता निकष):")}
                </div>
                {res.matched_rules.map((r: string, idx: number) => (
                  <div key={idx} style={{ lineHeight: 1.4 }}>✓ {r}</div>
                ))}
              </div>
            )}

            {/* Failed Rules */}
            {res.failed_rules && res.failed_rules.length > 0 && (
              <div style={{ backgroundColor: "#FEF2F2", padding: "12px", borderRadius: 12, fontSize: 12, color: "#991B1B" }}>
                <div style={{ fontWeight: 800, marginBottom: 4 }}>
                  {t("schemes.unmatched_rules", "अटी पूर्ण झालेल्या नाहीत:")}
                </div>
                {res.failed_rules.map((r: string, idx: number) => (
                  <div key={idx} style={{ lineHeight: 1.4 }}>✗ {r}</div>
                ))}
              </div>
            )}

            {/* Missing Info Input Questionnaire */}
            {res.missing_fields && res.missing_fields.length > 0 && (
              <div style={{ backgroundColor: "#FEF3C7", padding: "14px", borderRadius: 14, border: "1px solid #FDE68A" }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: "#92400E", marginBottom: 6 }}>
                  ⚠️ अधिक माहिती आवश्यक आहे ({res.missing_fields.length} Missing Fields)
                </div>
                <div style={{ fontSize: 12, color: "#78350F", marginBottom: 10 }}>
                  अचूक पात्रता निश्चितीसाठी खालील तपशील निवडा:
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {res.missing_fields.includes("has_bpl_ration_card") && (
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 700, color: "#451A03" }}>तुमच्याकडे BPL रेशन कार्ड आहे का?</label>
                      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                        <button
                          onClick={() => {
                            const updated = { ...missingFactsInput, has_bpl_ration_card: true, bpl_card_holder: true, social_category_or_bpl: "BPL" };
                            setMissingFactsInput(updated);
                            runSingleEligibilityCheck(schemeId, selectedBeneficiary, updated);
                          }}
                          style={{ flex: 1, padding: "8px", borderRadius: 8, border: "1px solid #CBD5E1", background: missingFactsInput.has_bpl_ration_card === true ? "#DBEAFE" : "#FFF", fontSize: 12, fontWeight: 700 }}
                        >
                          होय (Yes)
                        </button>
                        <button
                          onClick={() => {
                            const updated = { ...missingFactsInput, has_bpl_ration_card: false, bpl_card_holder: false };
                            setMissingFactsInput(updated);
                            runSingleEligibilityCheck(schemeId, selectedBeneficiary, updated);
                          }}
                          style={{ flex: 1, padding: "8px", borderRadius: 8, border: "1px solid #CBD5E1", background: missingFactsInput.has_bpl_ration_card === false ? "#DBEAFE" : "#FFF", fontSize: 12, fontWeight: 700 }}
                        >
                          नाही (No)
                        </button>
                      </div>
                    </div>
                  )}

                  {res.missing_fields.includes("child_order") && (
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 700, color: "#451A03" }}>हे कितवे बाळ आहे? (Child Order)</label>
                      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                        {[1, 2, 3].map(order => (
                          <button
                            key={order}
                            onClick={() => {
                              const updated = { ...missingFactsInput, child_order: order };
                              setMissingFactsInput(updated);
                              runSingleEligibilityCheck(schemeId, selectedBeneficiary, updated);
                            }}
                            style={{ flex: 1, padding: "8px", borderRadius: 8, border: "1px solid #CBD5E1", background: missingFactsInput.child_order === order ? "#DBEAFE" : "#FFF", fontSize: 12, fontWeight: 700 }}
                          >
                            {order === 1 ? "पहिले (1st)" : (order === 2 ? "दुसरे (2nd)" : "3+")}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Disclaimer */}
            <div style={{ fontSize: 11, color: "#64748B", fontStyle: "italic", borderTop: "1px solid #E2E8F0", paddingTop: 8 }}>
              {s?.official_verification_disclaimer || "शासकीय पडताळणी आवश्यक. हा प्राथमिक तपासणी निकाल मार्गदर्शनासाठी आहे."}
            </div>

            {/* Actions */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 6 }}>
              <button
                id="btn-eligibility-how-to-apply"
                onClick={() => navigateTo({ type: "how_to_apply", schemeId })}
                style={{
                  backgroundColor: "#1D4ED8",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: 12,
                  padding: "12px",
                  fontSize: 13,
                  fontWeight: 800,
                  cursor: "pointer",
                  minHeight: 48
                }}
              >
                {t("schemes.how_to_apply", "अर्ज कसा करावा")}
              </button>

              <button
                id="btn-eligibility-asha-help"
                onClick={() => handleRequestAshaAssistance(s || { scheme_code: schemeId })}
                style={{
                  backgroundColor: "#FDF2F8",
                  color: "#BE185D",
                  border: "1.5px solid #FBCFE8",
                  borderRadius: 12,
                  padding: "12px",
                  fontSize: 13,
                  fontWeight: 800,
                  cursor: "pointer",
                  minHeight: 48
                }}
              >
                {t("schemes.get_help_asha", "आशा मदत घ्या")}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    );
  };

  // =========================================================================
  // VIEW 5: HOW TO APPLY (/citizen/schemes/:schemeId/how-to-apply)
  // =========================================================================
  const renderHowToApplyView = (schemeId: string) => {
    const s = selectedSchemeDetail;
    const g = applicationGuidance;

    const steps = g?.application_steps || s?.application_steps || [
      "कागदपत्रे तयार ठेवा (Aadhaar, Ration Card, MCP Passbook)",
      "जवळच्या प्राथमिक आरोग्य केंद्र (PHC) किंवा आशा ताईंशी संपर्क साधा",
      "अधिकृत शासकीय पोर्टलवर पडताळणी पूर्ण करा",
      "लाभ बँक खात्यात किंवा रुग्णालयात कॅशलेस मिळवा"
    ];

    const officialUrl = g?.official_application_url || s?.official_application_url;
    const officialInfoUrl = g?.official_information_url || s?.official_information_url;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Top Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <button
            id="btn-back-to-detail-from-apply"
            onClick={() => navigateTo({ type: "scheme_detail", schemeId })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 700, minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" /> {t("common.back", "मागे")}
          </button>
          <h2 style={{ fontSize: 16, fontWeight: 800, color: "#0F172A", margin: 0 }}>
            {t("schemes.how_to_apply", "अर्ज प्रक्रिया मार्गदर्शक")}
          </h2>
        </div>

        {/* Scheme Name Banner */}
        <div style={{ backgroundColor: "#EFF6FF", borderRadius: 16, padding: "14px", border: "1px solid #BFDBFE" }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: "#1E3A8A" }}>
            {s?.official_scheme_name || s?.scheme_name || schemeId}
          </div>
          <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>
            प्राधिकरण: {s?.authority?.name || "शासकीय आरोग्य विभाग"}
          </div>
        </div>

        {/* Step-by-Step Instructions */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: 18, padding: "16px" }}>
          <h3 style={{ fontSize: 14, fontWeight: 800, color: "#0F172A", margin: "0 0 12px 0", display: "flex", alignItems: "center", gap: 6 }}>
            <CheckCircle2 size={16} color="#1D4ED8" /> {t("schemes.application_steps", "अर्ज कसा करावा? (Steps)")}
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {steps.map((step: string, idx: number) => (
              <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13, color: "#334155" }}>
                <span
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    backgroundColor: "#DBEAFE",
                    color: "#1D4ED8",
                    fontSize: 12,
                    fontWeight: 800,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0
                  }}
                >
                  {idx + 1}
                </span>
                <span style={{ lineHeight: 1.4 }}>{step}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 6 Application Actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Action 1: Apply on Official Portal */}
          {officialUrl && (
            <a
              id="btn-apply-official-portal"
              href={officialUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                backgroundColor: "#1D4ED8",
                color: "#FFFFFF",
                textDecoration: "none",
                borderRadius: 14,
                padding: "14px",
                fontSize: 14,
                fontWeight: 800,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                boxShadow: "0 4px 12px rgba(29, 78, 216, 0.2)",
                minHeight: 48
              }}
            >
              <Globe size={18} /> {t("schemes.apply_official_portal", "अधिकृत शासकीय पोर्टलवर अर्ज करा")} <ExternalLink size={14} />
            </a>
          )}

          {/* Action 2: Get Help From ASHA */}
          <button
            id="btn-get-help-asha"
            onClick={() => handleRequestAshaAssistance(s || { scheme_code: schemeId })}
            style={{
              backgroundColor: "#BE185D",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 14,
              padding: "14px",
              fontSize: 14,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48
            }}
          >
            <User size={18} /> {t("schemes.get_help_asha", "आशा ताईंची मदत घ्या (Get Help From ASHA)")}
          </button>

          {/* Action 3: Find Scheme Help Centre */}
          <button
            id="btn-find-scheme-desk"
            onClick={() => {
              navigateTo({ type: "help_centres", schemeId });
            }}
            style={{
              backgroundColor: "#FFFFFF",
              color: "#1E293B",
              border: "1.5px solid #CBD5E1",
              borderRadius: 14,
              padding: "12px",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48
            }}
          >
            <Building2 size={16} color="#1D4ED8" /> {t("schemes.find_help_centre", "मदत केंद्र शोधा (Find Help Desk)")}
          </button>


          {/* Action 4: Call Helpline */}
          <a
            id="btn-call-helpline"
            href={`tel:${s?.helpline || "104"}`}
            style={{
              backgroundColor: "#FFFFFF",
              color: "#166534",
              border: "1.5px solid #86EFAC",
              borderRadius: 14,
              padding: "12px",
              fontSize: 13,
              fontWeight: 700,
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48
            }}
          >
            <Phone size={16} color="#166534" /> {t("schemes.call_helpline", "हेल्पलाइनवर कॉल करा")} ({s?.helpline || "104 / 155388"})
          </a>

          {/* Action 5: Save Scheme */}
          <button
            id="btn-save-scheme"
            onClick={() => toggleSaveScheme(schemeId, s?.scheme_name || schemeId)}
            style={{
              backgroundColor: "#F8FAFC",
              color: "#475569",
              border: "1px solid #CBD5E1",
              borderRadius: 14,
              padding: "12px",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48
            }}
          >
            <Bookmark size={16} /> {t("schemes.save_scheme", "योजना जतन करा (Save Scheme)")}
          </button>
        </div>
      </div>
    );
  };

  // =========================================================================
  // VIEW 6: BENEFICIARY SELECTION MODAL (/citizen/schemes/check)
  // =========================================================================
  const renderBeneficiarySelectView = () => {
    const familyOptions = [
      {
        id: "myself",
        type: "MYSELF",
        name: `${user?.name || "मी स्वतः"} (Self)`,
        relation: "Self",
        age: 28,
        gender: "FEMALE",
        context: user?.village_name ? `गाव: ${user.village_name}` : "मुख्य लाभार्थी (Primary Beneficiary)",
        is_pregnant: true
      },
      ...householdMembers.map(m => ({
        id: m.id,
        type: "MEMBER",
        name: `${m.full_name || m.name} (${m.relationship_type || "Family Member"})`,
        relation: m.relationship_type || "Family",
        age: m.age || 30,
        gender: m.sex || m.gender || "FEMALE",
        context: m.health_notes || `${m.relationship_type || "सदस्य"} • ${m.age ? m.age + ' वर्षे' : ''}`,
        is_pregnant: Boolean(m.is_pregnant)
      }))
    ];

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={() => navigateTo({ type: "categories" })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" />
          </button>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              कोणासाठी योजना तपासायची आहे?
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>Select beneficiary for eligibility screening</div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {familyOptions.map((opt) => (
            <button
              key={opt.id}
              onClick={() => {
                setSelectedBeneficiary(opt);
                runFullScreening(opt);
              }}
              style={{
                backgroundColor: "#FFFFFF",
                border: "1.5px solid #E2E8F0",
                borderRadius: 16,
                padding: "16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer",
                textAlign: "left",
                minHeight: 64
              }}
            >
              <div>
                <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{opt.name}</div>
                <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>
                  {opt.age} वर्षे • {opt.gender} • {opt.context}
                </div>
              </div>
              <ChevronRight size={20} color="#94A3B8" />
            </button>
          ))}
        </div>
      </div>
    );
  };

  // =========================================================================
  // VIEW 7: BATCH SCREENING RESULTS
  // =========================================================================
  const renderAllScreeningResultsView = () => {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <button
            onClick={() => navigateTo({ type: "categories" })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" /> {t("common.back", "मागे")}
          </button>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              पात्रता निकाल ({selectedBeneficiary?.name || user?.name || "लाभार्थी"})
            </h2>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {allScreeningResults.map((r, idx) => {
            const badge = getStatusBadge(r.eligibility_status || r.status);
            return (
              <div
                key={idx}
                style={{
                  backgroundColor: "#FFFFFF",
                  border: "1.5px solid #E2E8F0",
                  borderRadius: 16,
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <h3 style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", margin: 0 }}>{r.scheme_name}</h3>
                  <span style={{ fontSize: 11, fontWeight: 800, padding: "3px 8px", borderRadius: 8, backgroundColor: badge.bg, color: badge.color }}>
                    {badge.label}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "#334155" }}>{r.summary}</div>
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                  <button
                    onClick={() => navigateTo({ type: "scheme_detail", schemeId: r.scheme_code })}
                    style={{ flex: 1, padding: "10px", borderRadius: 10, border: "none", backgroundColor: "#1D4ED8", color: "#FFF", fontSize: 12, fontWeight: 700, minHeight: 48 }}
                  >
                    तपशील पहा
                  </button>
                  <button
                    onClick={() => navigateTo({ type: "how_to_apply", schemeId: r.scheme_code })}
                    style={{ flex: 1, padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", backgroundColor: "#F8FAFC", color: "#334155", fontSize: 12, fontWeight: 700, minHeight: 48 }}
                  >
                    अर्ज करा
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // =========================================================================
  // VIEW 8: APPLICATIONS TRACKER
  // =========================================================================
  const renderApplicationsView = () => {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={() => navigateTo({ type: "categories" })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" />
          </button>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>माझे अर्ज व सहाय्य प्रगती</h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>Application & ASHA Assistance Tracker</div>
          </div>
        </div>

        {applications.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 16px", backgroundColor: "#F8FAFC", borderRadius: 16 }}>
            <Award size={40} color="#94A3B8" style={{ margin: "0 auto 8px auto" }} />
            <div style={{ fontSize: 14, fontWeight: 700, color: "#334155" }}>कोणताही सक्रिय अर्ज नाही</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {applications.map((appItem, idx) => (
              <div key={idx} style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 16, padding: "16px", display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{appItem.scheme_name || appItem.scheme_code}</div>
                  <span style={{ fontSize: 11, fontWeight: 800, padding: "3px 8px", borderRadius: 8, backgroundColor: "#FEF3C7", color: "#B45309" }}>
                    {appItem.status?.replace(/_/g, " ")}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "#64748B" }}>संदर्भ: {appItem.application_reference || "TRK-001"}</div>
                <div style={{ fontSize: 12, color: "#166534", fontWeight: 700, marginTop: 4 }}>
                  नियुक्त आशा: {appItem.assigned_asha_name || "Sita Patel (Kalyanpur)"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // =========================================================================
  // VIEW 9: SAVED BENEFITS
  // =========================================================================
  const renderSavedSchemesView = () => {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={() => navigateTo({ type: "categories" })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" />
          </button>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("schemes.saved_scheme", "जतन केलेल्या योजना (Saved)")}
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>Bookmarked Schemes ({savedSchemes.length})</div>
          </div>
        </div>

        {savedSchemes.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 16px", backgroundColor: "#F8FAFC", borderRadius: 16 }}>
            <Bookmark size={36} color="#94A3B8" style={{ margin: "0 auto 8px auto" }} />
            <div style={{ fontSize: 14, fontWeight: 700, color: "#475569" }}>कोणतीही योजना जतन केलेली नाही</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {savedSchemes.map((s, idx) => (
              <div
                key={idx}
                onClick={() => navigateTo({ type: "scheme_detail", schemeId: s.scheme_code || s.scheme_id })}
                style={{
                  backgroundColor: "#FFFFFF",
                  border: "1.5px solid #E2E8F0",
                  borderRadius: 16,
                  padding: "14px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  cursor: "pointer",
                  minHeight: 48
                }}
              >
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{s.scheme_name || s.scheme_code}</div>
                  <div style={{ fontSize: 11, color: "#64748B" }}>कोड: {s.scheme_code}</div>
                </div>
                <ChevronRight size={18} color="#94A3B8" />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // =========================================================================
  // VIEW 10: SCHEME HELP CENTRES (/citizen/schemes/:schemeId/help-centres)
  // =========================================================================
  const renderHelpCentresView = (schemeId: string) => {
    const s = selectedSchemeDetail;
    const reqs = helpRequirements;

    const handleGpsDetect = () => {
      setIsGpsLocating(true);
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const coords = { latitude: pos.coords.latitude, longitude: pos.coords.longitude, source: "DEVICE_GPS" };
            setUserCoordinates(coords);
            setLocationSource("CURRENT_GPS");
            setLocationAddressDisplay(`GPS Location (${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)})`);
            setIsGpsLocating(false);
            fetchSchemeHelpCentres(schemeId, coords, searchRadiusKm, "");
          },
          (err) => {
            console.warn("GPS failed or denied:", err);
            setIsGpsLocating(false);
            setLocationSource("MANUAL");
            setLocationAddressDisplay("Kalyanpur (Manual fallback)");
          },
          { timeout: 8000, enableHighAccuracy: true }
        );
      } else {
        setIsGpsLocating(false);
      }
    };

    const handleManualLocationSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      if (!manualVillageOrPin.trim()) return;
      setLocationSource("MANUAL");
      setLocationAddressDisplay(`${manualVillageOrPin.trim()} (Manual)`);
      fetchSchemeHelpCentres(schemeId, userCoordinates, searchRadiusKm, manualVillageOrPin.trim());
    };

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <button
            id="btn-back-to-scheme-from-centres"
            onClick={() => navigateTo({ type: "scheme_detail", schemeId })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 700, minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" /> {t("common.back", "मागे")}
          </button>
          <div style={{ textAlign: "right" }}>
            <h2 style={{ fontSize: 16, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("schemes.help_centres_title", "योजना मदत केंद्र")}
            </h2>
            <div style={{ fontSize: 11, color: "#64748B" }}>
              {s?.short_name || s?.scheme_code || schemeId}
            </div>
          </div>
        </div>

        {/* Scheme & Capability Banner */}
        <div id="required-capabilities-banner" style={{ backgroundColor: "#EFF6FF", border: "1.5px solid #BFDBFE", borderRadius: 16, padding: "14px" }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#1E40AF", marginBottom: 4 }}>
            {s?.official_scheme_name || s?.scheme_name || schemeId}
          </div>
          <div style={{ fontSize: 12, color: "#1E293B", marginBottom: 6 }}>
            <strong>{t("schemes.required_capabilities_label", "आवश्यक केंद्र सुविधा:")}</strong>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {(reqs?.required_capabilities || []).map((c, idx) => (
              <span
                key={idx}
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  backgroundColor: "#DBEAFE",
                  color: "#1E40AF",
                  padding: "4px 8px",
                  borderRadius: 8
                }}
              >
                ✓ {c.name}
              </span>
            ))}
          </div>
          <div style={{ fontSize: 11, color: "#64748B", marginTop: 8, fontStyle: "italic" }}>
            ⚠️ {t("schemes.documents_disclaimer", "अंतिम कागदपत्रे आणि पात्रता पडताळणी केवळ संबंधित सरकारी प्राधिकरणाद्वारे केली जाते.")}
          </div>
        </div>

        {/* Location Selection Controls */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: 16, padding: "16px" }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: "#0F172A", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
            <MapPin size={16} color="#1D4ED8" /> {t("schemes.confirm_location", "तुमचे ठिकाण निवडा (Confirm Location)")}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
            <button
              id="btn-use-current-location"
              onClick={handleGpsDetect}
              disabled={isGpsLocating}
              style={{
                backgroundColor: locationSource === "CURRENT_GPS" ? "#DBEAFE" : "#F8FAFC",
                color: locationSource === "CURRENT_GPS" ? "#1D4ED8" : "#334155",
                border: `1.5px solid ${locationSource === "CURRENT_GPS" ? "#93C5FD" : "#CBD5E1"}`,
                borderRadius: 10,
                padding: "10px 8px",
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
              <Compass size={14} /> {isGpsLocating ? "शोधत आहे..." : t("schemes.use_current_location", "GPS वापरा")}
            </button>

            <button
              id="btn-use-registered-address"
              onClick={() => {
                setLocationSource("REGISTERED_ADDRESS");
                setUserCoordinates({ latitude: 18.5204, longitude: 73.8567, source: "REGISTERED_HOME" });
                setLocationAddressDisplay("Kalyanpur Gaothan (Registered)");
                fetchSchemeHelpCentres(schemeId, { latitude: 18.5204, longitude: 73.8567 }, searchRadiusKm, "Kalyanpur");
              }}
              style={{
                backgroundColor: locationSource === "REGISTERED_ADDRESS" ? "#DBEAFE" : "#F8FAFC",
                color: locationSource === "REGISTERED_ADDRESS" ? "#1D4ED8" : "#334155",
                border: `1.5px solid ${locationSource === "REGISTERED_ADDRESS" ? "#93C5FD" : "#CBD5E1"}`,
                borderRadius: 10,
                padding: "10px 8px",
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
              <Building2 size={14} /> {t("schemes.use_registered_address", "नोंदणीकृत पत्ता")}
            </button>
          </div>

          {/* Manual Village / PIN Entry Form */}
          <form onSubmit={handleManualLocationSubmit} style={{ display: "flex", gap: 8 }}>
            <input
              id="input-manual-location"
              type="text"
              placeholder={t("schemes.enter_village_pin", "गाव किंवा पिनकोड टाका...")}
              value={manualVillageOrPin}
              onChange={(e) => setManualVillageOrPin(e.target.value)}
              style={{
                flex: 1,
                padding: "10px 12px",
                borderRadius: 10,
                border: "1.5px solid #CBD5E1",
                fontSize: 13,
                outline: "none"
              }}
            />
            <button
              id="btn-submit-manual-location"
              type="submit"
              style={{
                backgroundColor: "#1D4ED8",
                color: "#FFF",
                border: "none",
                borderRadius: 10,
                padding: "10px 16px",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                minHeight: 44
              }}
            >
              {t("common.search", "शोधा")}
            </button>
          </form>

          <div style={{ marginTop: 8, fontSize: 11, color: "#64748B", display: "flex", justifyContent: "space-between" }}>
            <span>स्थान: <strong>{locationAddressDisplay}</strong></span>
            <button
              onClick={() => setShowMapView(!showMapView)}
              style={{ border: "none", background: "none", color: "#1D4ED8", fontWeight: 700, cursor: "pointer", fontSize: 11 }}
            >
              {showMapView ? "लपवा नकाशा" : "नकाशा पहा"}
            </button>
          </div>
        </div>

        {/* Optional Google Map View */}
        {showMapView && userCoordinates && (
          <div style={{ borderRadius: 16, overflow: "hidden", border: "1px solid #CBD5E1", height: 260 }}>
            <GoogleMapView
              userLocation={userCoordinates}
              facilities={helpCentres as any}
              selectedFacilityId={null}
              onSelectFacility={(fac) => navigateTo({ type: "help_centre_detail", schemeId, facilityId: fac.facility_id || fac.id })}
            />
          </div>
        )}

        {/* Help Centre Results Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", margin: 0 }}>
            सत्यापित मदत केंद्रे ({(Array.isArray(helpCentres) ? helpCentres : []).length})
          </h3>
          <span style={{ fontSize: 12, color: "#64748B" }}>दायरा: {searchRadiusKm} किमी</span>
        </div>

        {/* Empty State with Working Alternatives */}
        {(Array.isArray(helpCentres) ? helpCentres : []).length === 0 && !loading && (
          <div style={{ backgroundColor: "#FFFBEB", border: "1.5px solid #FDE68A", borderRadius: 16, padding: "20px", textAlign: "center" }}>
            <AlertTriangle size={32} color="#D97706" style={{ margin: "0 auto 8px auto" }} />
            <div style={{ fontSize: 14, fontWeight: 800, color: "#92400E", marginBottom: 6 }}>
              {t("schemes.no_help_centres_found", "जवळपास कोणतेही सत्यापित योजना मदत केंद्र आढळले नाही.")}
            </div>
            <div style={{ fontSize: 12, color: "#78350F", marginBottom: 14 }}>
              आपण शोध अंतर वाढवू शकता, आपल्या आशा कार्यकर्तीशी संपर्क साधू शकता किंवा अधिकृत हेल्पलाईनवर कॉल करू शकता.
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button
                id="btn-expand-search"
                onClick={() => {
                  setSearchRadiusKm(100);
                  fetchSchemeHelpCentres(schemeId, userCoordinates, 100, manualVillageOrPin);
                }}
                style={{
                  backgroundColor: "#1D4ED8",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 10,
                  padding: "10px",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  minHeight: 44
                }}
              >
                {t("schemes.expand_search", "शोध वाढवा (100 किमी)")}
              </button>
              <button
                id="btn-empty-ask-asha"
                onClick={() => handleRequestAshaAssistance(s || { scheme_code: schemeId })}
                style={{
                  backgroundColor: "#BE185D",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 10,
                  padding: "10px",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  minHeight: 44
                }}
              >
                {t("schemes.ask_asha_for_help", "आशा ताईंची मदत घ्या")}
              </button>
            </div>
          </div>
        )}

        {/* Results List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {(Array.isArray(helpCentres) ? helpCentres : []).map((centre, idx) => {

            const isVerified = centre.verification_status === "VERIFIED";
            return (
              <div
                key={idx}
                id={`help-centre-card-${centre.facility_id}`}
                style={{
                  backgroundColor: "#FFFFFF",
                  border: `1.5px solid ${centre.exact_capability_match ? "#93C5FD" : "#E2E8F0"}`,
                  borderRadius: 16,
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
                }}
              >
                {/* Title & Badge */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                      {centre.name || centre.display_name}
                    </div>
                    <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>
                      {centre.facility_type_label || centre.facility_type} • {centre.authority}
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 800,
                      backgroundColor: isVerified ? "#DCFCE7" : "#FEF3C7",
                      color: isVerified ? "#15803D" : "#92400E",
                      padding: "4px 8px",
                      borderRadius: 8,
                      flexShrink: 0
                    }}
                  >
                    {isVerified ? "✓ " + t("schemes.verified_centre", "सत्यापित केंद्र") : "⚠️ " + t("schemes.unverified_centre", "अनपेक्षित")}
                  </span>
                </div>

                {/* Scheme capability matched */}
                <div style={{ backgroundColor: "#F8FAFC", borderRadius: 8, padding: "8px", fontSize: 12, color: "#334155" }}>
                  <strong>सुविधा:</strong> {centre.matching_capabilities?.join(", ") || "योजना मदत कक्ष व e-KYC"}
                </div>

                {/* Distance, Travel Time & Address */}
                <div style={{ fontSize: 12, color: "#64748B", display: "flex", flexDirection: "column", gap: 2 }}>
                  <div>
                    <MapPin size={13} style={{ display: "inline", marginRight: 4 }} />
                    {centre.address || centre.village || "Kalyanpur Main Area"} • <strong>{centre.distance_km} किमी ({centre.travel_time_text})</strong>
                  </div>
                  <div>
                    <Clock size={13} style={{ display: "inline", marginRight: 4 }} />
                    {centre.operating_status_label}
                  </div>
                </div>

                {/* 6 Working Action Buttons */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 6 }}>
                  {centre.phone ? (
                    <a
                      id={`btn-call-centre-${centre.facility_id}`}
                      href={`tel:${centre.phone}`}
                      style={{
                        backgroundColor: "#16A34A",
                        color: "#FFF",
                        textDecoration: "none",
                        padding: "10px",
                        borderRadius: 10,
                        fontSize: 12,
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 6,
                        minHeight: 44
                      }}
                    >
                      <Phone size={14} /> {t("schemes.call_centre", "कॉल करा")}
                    </a>
                  ) : (
                    <button
                      disabled
                      style={{
                        backgroundColor: "#F1F5F9",
                        color: "#94A3B8",
                        border: "none",
                        padding: "10px",
                        borderRadius: 10,
                        fontSize: 12,
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 6,
                        minHeight: 44
                      }}
                    >
                      <Phone size={14} /> फोन उपलब्ध नाही
                    </button>
                  )}

                  <a
                    id={`btn-directions-${centre.facility_id}`}
                    href={centre.google_maps_directions_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      backgroundColor: "#1D4ED8",
                      color: "#FFF",
                      textDecoration: "none",
                      padding: "10px",
                      borderRadius: 10,
                      fontSize: 12,
                      fontWeight: 700,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      minHeight: 44
                    }}
                  >
                    <Navigation size={14} /> {t("schemes.directions", "दिशा-मार्ग")}
                  </a>

                  <button
                    id={`btn-view-details-${centre.facility_id}`}
                    onClick={() => navigateTo({ type: "help_centre_detail", schemeId, facilityId: centre.facility_id })}
                    style={{
                      backgroundColor: "#EFF6FF",
                      color: "#1D4ED8",
                      border: "1px solid #BFDBFE",
                      padding: "10px",
                      borderRadius: 10,
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
                    <Building2 size={14} /> {t("schemes.view_details", "सविस्तर माहिती")}
                  </button>

                  <button
                    id={`btn-ask-asha-centre-${centre.facility_id}`}
                    onClick={() => handleRequestAshaAssistance(s || { scheme_code: schemeId })}
                    style={{
                      backgroundColor: "#FDF2F8",
                      color: "#BE185D",
                      border: "1px solid #FBCFE8",
                      padding: "10px",
                      borderRadius: 10,
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
                    <User size={14} /> {t("schemes.ask_asha_for_help", "आशा मदत")}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // =========================================================================
  // VIEW 11: SCHEME HELP CENTRE DETAIL
  // (/citizen/schemes/:schemeId/help-centres/:facilityId)
  // =========================================================================
  const renderHelpCentreDetailView = (schemeId: string, facilityId: string) => {
    const d = selectedFacilityDetail;
    const fac = d?.facility;
    const s = d?.scheme || selectedSchemeDetail;

    if (!d || !fac) {
      return (
        <div style={{ textAlign: "center", padding: 40 }}>
          {errorMsg ? (
            <div>
              <div style={{ color: "#DC2626", fontWeight: 700, marginBottom: 12 }}>{errorMsg}</div>
              <button
                onClick={() => navigateTo({ type: "help_centres", schemeId })}
                style={{ padding: "10px 16px", borderRadius: 10, backgroundColor: "#1D4ED8", color: "#FFF", border: "none" }}
              >
                मदत केंद्रांकडे परत जा
              </button>
            </div>
          ) : (
            <div>मदत केंद्राची माहिती लोड होत आहे...</div>
          )}
        </div>
      );
    }

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Top Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <button
            id="btn-back-to-centres-list"
            onClick={() => navigateTo({ type: "help_centres", schemeId })}
            style={{ border: "none", background: "#F1F5F9", padding: "10px 14px", borderRadius: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 700, minHeight: 48 }}
          >
            <ArrowLeft size={18} color="#1E293B" /> {t("common.back", "मागे")}
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => speakText(`${fac.name}. ${fac.address}. Contact: ${fac.phone || "Helpline 104"}`)}
              style={{ border: "none", background: "#F1F5F9", padding: 10, borderRadius: 12, cursor: "pointer", minHeight: 48 }}
              aria-label="Read Aloud"
            >
              <Volume2 size={18} color="#1E293B" />
            </button>
          </div>
        </div>

        {/* Facility Header */}
        <div>
          <span style={{ fontSize: 11, fontWeight: 800, color: "#15803D", backgroundColor: "#DCFCE7", padding: "4px 8px", borderRadius: 8 }}>
            ✓ {fac.verification_status} • {fac.facility_type_label}
          </span>
          <h1 style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: "8px 0 4px 0" }}>
            {fac.official_name || fac.name}
          </h1>
          <div style={{ fontSize: 12, color: "#64748B" }}>
            {fac.authority} • {fac.district}, {fac.state}
          </div>
        </div>

        {/* Scheme Association Badge */}
        <div style={{ backgroundColor: "#EFF6FF", border: "1.5px solid #BFDBFE", borderRadius: 14, padding: "12px" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#1E40AF" }}>
            संबंधित योजना: <strong>{s?.scheme_name || schemeId}</strong>
          </div>
          <div style={{ fontSize: 11, color: "#3B82F6", marginTop: 2 }}>
            या केंद्रात योजनेचे फॉर्म, e-KYC आणि नोंदणी सहाय्य उपलब्ध आहे.
          </div>
        </div>

        {/* Documents to Carry */}
        <div style={{ backgroundColor: "#FFFFFF", border: "1.5px solid #E2E8F0", borderRadius: 16, padding: "16px" }}>
          <h3 style={{ fontSize: 14, fontWeight: 800, color: "#0F172A", margin: "0 0 8px 0", display: "flex", alignItems: "center", gap: 6 }}>
            <FileText size={16} color="#1D4ED8" /> {t("schemes.documents_to_carry", "केंद्रावर जाताना सोबत नेण्याची कागदपत्रे")}
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {d.required_documents?.general?.map((doc, idx) => (
              <div key={idx} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#334155" }}>
                <CheckCircle2 size={16} color="#16A34A" />
                <span>{doc}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 12, fontSize: 11, color: "#64748B", fontStyle: "italic" }}>
            ⚠️ {d.application_guidance?.verification_disclaimer || "Final document and eligibility verification is performed solely by the responsible government authority."}
          </div>
        </div>

        {/* Operating Hours */}
        <div style={{ backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 16, padding: "16px" }}>
          <h3 style={{ fontSize: 14, fontWeight: 800, color: "#0F172A", margin: "0 0 8px 0", display: "flex", alignItems: "center", gap: 6 }}>
            <Clock size={16} color="#1D4ED8" /> {t("schemes.opening_hours", "कामाची वेळ व संपर्क")}
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, color: "#334155" }}>
            <div>• <strong>पत्ता:</strong> {fac.address || "Main Road, Kalyanpur Block"}</div>
            <div>• <strong>वेळ:</strong> {d.operating_hours?.[0]?.hours_display || "09:00 AM - 05:00 PM"}</div>
            <div>• <strong>फोन:</strong> {fac.phone || "104"}</div>
            <div>• <strong>अंतर:</strong> {fac.distance_km} किमी ({fac.travel_time_text})</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {fac.phone && (
            <a
              id="btn-detail-call"
              href={`tel:${fac.phone}`}
              style={{
                backgroundColor: "#16A34A",
                color: "#FFF",
                textDecoration: "none",
                padding: "14px",
                borderRadius: 14,
                fontSize: 13,
                fontWeight: 800,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                minHeight: 48
              }}
            >
              <Phone size={16} /> {t("schemes.call_centre", "कॉल करा")}
            </a>
          )}

          <a
            id="btn-detail-directions"
            href={fac.google_maps_directions_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              backgroundColor: "#1D4ED8",
              color: "#FFF",
              textDecoration: "none",
              padding: "14px",
              borderRadius: 14,
              fontSize: 13,
              fontWeight: 800,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              minHeight: 48
            }}
          >
            <Navigation size={16} /> {t("schemes.directions", "दिशा-मार्ग")}
          </a>
        </div>

        <button
          id="btn-detail-ask-asha"
          onClick={() => handleRequestAshaAssistance(s || { scheme_code: schemeId })}
          style={{
            backgroundColor: "#BE185D",
            color: "#FFF",
            border: "none",
            borderRadius: 14,
            padding: "14px",
            fontSize: 13,
            fontWeight: 800,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            minHeight: 48
          }}
        >
          <User size={18} /> {t("schemes.ask_asha_for_help", "आशा ताईंची मदत घ्या (Get Help From ASHA)")}
        </button>
      </div>
    );
  };

  return (
    <div style={{ padding: "16px", paddingBottom: "80px", maxWidth: 480, margin: "0 auto" }}>
      {/* Toast Feedback Notification */}
      {actionSuccessMsg && (
        <div
          id="action-toast-notification"
          style={{
            position: "fixed",
            top: 20,
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "#15803D",
            color: "#FFFFFF",
            padding: "12px 20px",
            borderRadius: 20,
            fontSize: 13,
            fontWeight: 800,
            boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
            zIndex: 9999
          }}
        >
          {actionSuccessMsg}
        </div>

      )}

      {/* Global Error Banner with Retry */}
      {errorMsg && (
        <div
          style={{
            backgroundColor: "#FEF2F2",
            border: "1.5px solid #FCA5A5",
            borderRadius: 14,
            padding: "12px 14px",
            marginBottom: 16,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 8,
            fontSize: 13,
            color: "#991B1B",
            fontWeight: 700
          }}
        >
          <span>{errorMsg}</span>
          <button
            onClick={() => {
              setErrorMsg(null);
              loadInitialData();
            }}
            style={{
              border: "none",
              backgroundColor: "#DC2626",
              color: "#FFF",
              padding: "6px 12px",
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer"
            }}
          >
            {t("common.retry", "पुन्हा प्रयत्न करा")}
          </button>
        </div>
      )}

      {/* Dynamic Route Render */}
      {routeState.type === "categories" && renderCategoriesView()}
      {routeState.type === "category_list" && renderCategoryListView(routeState.categoryId)}
      {routeState.type === "scheme_detail" && renderSchemeDetailView(routeState.schemeId)}
      {routeState.type === "eligibility" && renderEligibilityView(routeState.schemeId)}
      {routeState.type === "how_to_apply" && renderHowToApplyView(routeState.schemeId)}
      {routeState.type === "check_beneficiary" && renderBeneficiarySelectView()}
      {routeState.type === "all_screening_results" && renderAllScreeningResultsView()}
      {routeState.type === "saved_schemes" && renderSavedSchemesView()}
      {routeState.type === "applications" && renderApplicationsView()}
      {(routeState.type === "help_centres" || (routeState as any).type === "help_centres") && (
        <div id="help-centres-container">
          {renderHelpCentresView((routeState as any).schemeId)}
        </div>
      )}
      {routeState.type === "help_centre_detail" && renderHelpCentreDetailView(routeState.schemeId, routeState.facilityId)}

    </div>
  );
};

export default SchemesScreen;

