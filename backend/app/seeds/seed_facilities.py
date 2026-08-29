import logging
from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from app.models.facilities import (
    Facility, FacilityService, FacilityHours, FacilitySchemeEmpanelment,
    FacilityTypeEnum, FacilityOwnershipEnum, VerificationStatusEnum,
    ServiceAvailabilityStatusEnum
)

logger = logging.getLogger("aarogya.seeds.facilities")

DEMO_FACILITIES = [
    {
        "public_reference": "FAC-2026-001",
        "code": "SC-GANESHPUR-01",
        "official_name": "Ganeshpur Ayushman Arogya Mandir (Sub-Centre)",
        "name": "Ganeshpur Sub-Centre",
        "localized_name": {
            "mr-IN": "गणेशपूर उपकेंद्र (आयुष्मान आरोग्य मंदिर)",
            "hi-IN": "गणेशपुर उप-स्वास्थ्य केंद्र",
            "en-IN": "Ganeshpur Sub-Centre (Arogya Mandir)"
        },
        "facility_type": FacilityTypeEnum.SUB_CENTRE,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "Public Health Department, Maharashtra",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Ganeshpur",
        "pincode": "415001",
        "address": "Ganeshpur Gaothan, Near Gram Panchayat Office",
        "landmark": "Opposite Zilla Parishad Primary School",
        "latitude": 18.5204,
        "longitude": 73.8567, # ~1.2 km from Kalyanpur base
        "phone": "+91 2162 254101",
        "email": "sc.ganeshpur@health.maharashtra.gov.in",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "GOVT_REGISTRY_NIN_415001",
        "source_name": "National Health Portal Facility Registry",
        "last_verified_at": datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "MONDAY", "opening_time": "09:00", "closing_time": "14:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "TUESDAY", "opening_time": "09:00", "closing_time": "14:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "WEDNESDAY", "opening_time": "09:00", "closing_time": "14:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "THURSDAY", "opening_time": "09:00", "closing_time": "14:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "FRIDAY", "opening_time": "09:00", "closing_time": "14:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "SATURDAY", "opening_time": "09:00", "closing_time": "13:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "GENERAL_OPD",
                "localized_service_name": {"mr-IN": "प्राथमिक तपासणी", "hi-IN": "प्राथमिक जांच", "en-IN": "Primary Health Screening & OPD"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "CHILD_VACCINATION",
                "localized_service_name": {"mr-IN": "नियमित बाल लसीकरण (बुधवार)", "hi-IN": "नियमित टीकाकरण", "en-IN": "Routine Child Immunization (Wednesdays)"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "ANTENATAL_CARE",
                "localized_service_name": {"mr-IN": "गरोदर महिला तपासणी (ANC)", "hi-IN": "गर्भावस्था जांच", "en-IN": "Antenatal Care Screening (ANC)"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "MATERNITY_DELIVERY",
                "localized_service_name": {"mr-IN": "प्रसूती सेवा (उपलब्ध नाही - PHC ला पाठवले जाते)", "hi-IN": "प्रसव सेवा (उपलब्ध नहीं)", "en-IN": "Maternity Inpatient Delivery (Not Available)"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.UNAVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "EMERGENCY_24X7",
                "localized_service_name": {"mr-IN": "२४x७ आपत्कालीन सेवा (उपलब्ध नाही)", "hi-IN": "आपातकालीन सेवा (उपलब्ध नहीं)", "en-IN": "24x7 Emergency (Not Available)"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.UNAVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {
                "scheme_code": "JSY",
                "scheme_name": "Janani Suraksha Yojana (Registration Desk)",
                "empanelment_reference": "MH-JSY-REG-2026-04",
                "verification_status": VerificationStatusEnum.VERIFIED,
                "official_source": "NHM Maharashtra"
            }
        ]
    },
    {
        "public_reference": "FAC-2026-002",
        "code": "PHC-09",
        "official_name": "Kalyanpur Primary Health Centre (PHC)",
        "name": "Kalyanpur Primary Health Centre",
        "localized_name": {
            "mr-IN": "कल्याणपूर प्राथमिक आरोग्य केंद्र (PHC)",
            "hi-IN": "कल्याणपुर प्राथमिक स्वास्थ्य केंद्र",
            "en-IN": "Kalyanpur Primary Health Centre (PHC)"
        },
        "facility_type": FacilityTypeEnum.PHC,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "Zilla Parishad & Health Dept, Maharashtra",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Kalyanpur",
        "pincode": "415001",
        "address": "PHC Road, Main Market, Kalyanpur",
        "landmark": "Near Kalyanpur Bus Stand & Taluka Panchayat",
        "latitude": 18.5300,
        "longitude": 73.8700, # ~2.8 km
        "phone": "+91 2162 234567",
        "email": "phc.kalyanpur@health.maharashtra.gov.in",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "GOVT_REGISTRY_NIN_415002",
        "source_name": "Directorate of Health Services Maharashtra",
        "last_verified_at": datetime(2026, 8, 26, 9, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "00:00", "closing_time": "23:59", "is_24x7_emergency": True, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "GENERAL_OPD",
                "localized_service_name": {"mr-IN": "सामान्य बाह्यरुग्ण विभाग (OPD)", "hi-IN": "सामान्य ओपीडी", "en-IN": "General OPD Medical Officer"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "EMERGENCY_24X7",
                "localized_service_name": {"mr-IN": "२४x७ आपत्कालीन व प्रथमोपचार", "hi-IN": "24x7 आपातकालीन देखभाल", "en-IN": "24x7 Emergency First Aid & Stabilization"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "MATERNITY_DELIVERY",
                "localized_service_name": {"mr-IN": "२४ तास मोफत प्रसूती कक्ष व रुग्णवाहिका", "hi-IN": "24x7 सामान्य प्रसव वार्ड", "en-IN": "24x7 Normal Delivery Labor Room"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "CHILD_VACCINATION",
                "localized_service_name": {"mr-IN": "सर्वसमावेशक बाल लसीकरण केंद्र", "hi-IN": "सम्पूर्ण बाल टीकाकरण", "en-IN": "Complete Child Immunization & Cold Chain"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "PATHOLOGY_XRAY",
                "localized_service_name": {"mr-IN": "प्राथमिक रक्त व लघवी चाचण्या प्रयोगशाळा", "hi-IN": "प्राथमिक लैब टेस्ट", "en-IN": "Basic Pathology Lab (CBC, Malaria, Dengue, Blood Sugar)"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "TB_DOTS",
                "localized_service_name": {"mr-IN": "निक्षय टीबी तपासणी व औषधोपचार", "hi-IN": "टीबी जांच व उपचार", "en-IN": "Nikshay TB Screening & DOTS Centre"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "NCD_DIABETES_BP",
                "localized_service_name": {"mr-IN": "मधुमेह व रक्तदाब क्लिनिक (NCD)", "hi-IN": "बीपी व शुगर क्लिनिक", "en-IN": "Hypertension & Diabetes NCD Clinic"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "PHARMACY",
                "localized_service_name": {"mr-IN": "शासकीय मोफत औषधालय", "hi-IN": "सरकारी मुफ्त दवाखाना", "en-IN": "Govt Free Essential Drug Dispensary"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "AYUSHMAN_HELP_DESK",
                "localized_service_name": {"mr-IN": "आयुष्मान भारत / महात्मा फुले योजना कक्ष", "hi-IN": "आयुष्मान मित्र हेल्प डेस्क", "en-IN": "Ayushman Bharat PM-JAY Help Desk"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat PM-JAY (Primary Desk & e-KYC)", "empanelment_reference": "MH-PMJAY-PHC-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHA Portal"},
            {"scheme_code": "MJPJAY", "scheme_name": "Mahatma Jyotirao Phule Jan Arogya Yojana", "empanelment_reference": "MJPJAY-PHC-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "SHAS Maharashtra"},
            {"scheme_code": "JSY", "scheme_name": "Janani Suraksha Yojana Cash Assistance", "empanelment_reference": "JSY-KALYANPUR-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHM Maharashtra"},
            {"scheme_code": "JSSK", "scheme_name": "Janani Shishu Suraksha Karyakram (Free Transport & Food)", "empanelment_reference": "JSSK-KALYANPUR-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHM Maharashtra"},
            {"scheme_code": "PMMVY", "scheme_name": "Pradhan Mantri Matru Vandana Yojana Desk", "empanelment_reference": "PMMVY-KALYANPUR-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "WCD Maharashtra"}
        ]
    },
    {
        "public_reference": "FAC-2026-003",
        "code": "CHC-KALYANPUR-01",
        "official_name": "Kalyanpur Community Health Centre (CHC / Rural Hospital)",
        "name": "Kalyanpur Community Health Centre",
        "localized_name": {
            "mr-IN": "कल्याणपूर ग्रामीण रुग्णालय (CHC)",
            "hi-IN": "कल्याणपुर सामुदायिक स्वास्थ्य केंद्र",
            "en-IN": "Kalyanpur Community Health Centre (CHC)"
        },
        "facility_type": FacilityTypeEnum.CHC,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "Public Health Department, Maharashtra",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Taluka Headquarters",
        "pincode": "415002",
        "address": "Hospital Road, Taluka Headquarter, Kalyanpur",
        "landmark": "Near Civil Court & Taluka Police Station",
        "latitude": 18.5600,
        "longitude": 73.9000, # ~8.5 km
        "phone": "+91 2162 278910",
        "email": "chc.kalyanpur@health.maharashtra.gov.in",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "GOVT_REGISTRY_NIN_415003",
        "source_name": "National Health Portal Facility Registry",
        "last_verified_at": datetime(2026, 8, 24, 14, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "00:00", "closing_time": "23:59", "is_24x7_emergency": True, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "EMERGENCY_24X7",
                "localized_service_name": {"mr-IN": "२४x७ आपत्कालीन व शस्त्रक्रिया विभाग", "hi-IN": "24x7 आपातकालीन एवं ट्रॉमा", "en-IN": "24x7 Emergency & Trauma Stabilization"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "MATERNITY_DELIVERY",
                "localized_service_name": {"mr-IN": "सिझेरियन व गुंतागुंतीची प्रसूती (FRU)", "hi-IN": "सिजेरियन व सुरक्षित प्रसव", "en-IN": "Comprehensive Emergency Obstetric Care (CEmOC / C-Section)"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "CHILD_VACCINATION",
                "localized_service_name": {"mr-IN": "बालरोग तज्ज्ञ ओपीडी व नवजात कक्ष (SNCU)", "hi-IN": "बालरोग विशेषज्ञ व शिशु देखभाल", "en-IN": "Pediatrician OPD & Special Newborn Care Unit (SNCU)"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "PATHOLOGY_XRAY",
                "localized_service_name": {"mr-IN": "डिजिटल एक्स-रे व संपूर्ण प्रयोगशाळा", "hi-IN": "डिजिटल एक्स-रे व पूर्ण पैथोलॉजी", "en-IN": "Digital X-Ray, Sonography & Full Pathology Lab"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "SURGERY",
                "localized_service_name": {"mr-IN": "सामान्य शस्त्रक्रिया व ऑपरेशन थिएटर (OT)", "hi-IN": "सामान्य शल्य चिकित्सा एवं ओटी", "en-IN": "General Surgery & Operation Theatre (OT)"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat PM-JAY Cashless Hospitalization", "empanelment_reference": "MH-PMJAY-CHC-01", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHA Portal"},
            {"scheme_code": "MJPJAY", "scheme_name": "Mahatma Jyotirao Phule Jan Arogya Yojana", "empanelment_reference": "MJPJAY-CHC-01", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "SHAS Maharashtra"}
        ]
    },
    {
        "public_reference": "FAC-2026-004",
        "code": "DH-DISTRICT04-01",
        "official_name": "District Hospital District 04 (Tertiary Care Centre)",
        "name": "District Hospital District 04",
        "localized_name": {
            "mr-IN": "जिल्हा सामान्य रुग्णालय व वैद्यकीय केंद्र",
            "hi-IN": "जिला अस्पताल व तृतीयक देखभाल केंद्र",
            "en-IN": "District Hospital District 04 (Tertiary Care Centre)"
        },
        "facility_type": FacilityTypeEnum.DISTRICT_HOSPITAL,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "Directorate of Medical Education & Health, Maharashtra",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "District HQ",
        "village": "District Centre",
        "pincode": "415000",
        "address": "Civil Lines Road, District 04",
        "landmark": "Opposite District Collectorate & Central Bus Stand",
        "latitude": 18.6200,
        "longitude": 73.9500, # ~18.0 km
        "phone": "+91 2162 222100",
        "email": "cs.districthospital@maharashtra.gov.in",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "GOVT_REGISTRY_NIN_415004",
        "source_name": "National Health Portal Facility Registry",
        "last_verified_at": datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "00:00", "closing_time": "23:59", "is_24x7_emergency": True, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "EMERGENCY_24X7",
                "localized_service_name": {"mr-IN": "२४x७ अतिदक्षता (ICU), ट्रॉमा व हृदयविकार आपत्कालीन केंद्र", "hi-IN": "24x7 ट्रॉमा, आईसीयू व हृदय देखभाल", "en-IN": "Level 1 Trauma, Cardiac Care Unit (CCU), 24x7 Emergency ICU"},
                "service_level": "TERTIARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "SURGERY",
                "localized_service_name": {"mr-IN": "प्रमुख शस्त्रक्रिया, लॅपरोस्कोपी व मॉड्यूलर ओटी", "hi-IN": "मेजर सर्जरी, लेप्रोस्कोपी व ऑपरेशन थिएटर", "en-IN": "Major General Surgery, Laparoscopy & Modular Operation Theatre"},
                "service_level": "TERTIARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "MATERNITY_DELIVERY",
                "localized_service_name": {"mr-IN": "अती जोखमीची प्रसूती, एनआयसीयू (NICU) व स्त्रीरोग विभाग", "hi-IN": "उच्च जोखिम प्रसव व एनआईसीयू", "en-IN": "High-Risk Obstetrics, Gynaecology, Neonatal ICU (NICU)"},
                "service_level": "TERTIARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "PATHOLOGY_XRAY",
                "localized_service_name": {"mr-IN": "सीटी स्कॅन, एमआरआय, रक्तपेढी व सर्वसमावेशक प्रयोगशाळा", "hi-IN": "सीटी स्कैन, एमआरआई व ब्लड बैंक", "en-IN": "CT Scan, MRI, 24x7 Blood Bank, Advanced Pathology"},
                "service_level": "TERTIARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "FREE"
            },
            {
                "service_code": "TB_DOTS",
                "localized_service_name": {"mr-IN": "जिल्हा टीबी केंद्र व औषध प्रतिरोधक टीबी (DR-TB) विभाग", "hi-IN": "जिला टीबी केंद्र", "en-IN": "District TB Centre & Drug-Resistant TB Ward"},
                "service_level": "TERTIARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],

        "schemes": [
            {"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat PM-JAY Cashless Tertiary Hospitalization", "empanelment_reference": "MH-PMJAY-DH-04", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHA Official Registry"},
            {"scheme_code": "MJPJAY", "scheme_name": "MJPJAY State Assurance Cashless Surgeries", "empanelment_reference": "MJPJAY-DH-04", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "SHAS Maharashtra"}
        ]
    },
    {
        "public_reference": "FAC-2026-005",
        "code": "PVT-LIFECARE-01",
        "official_name": "LifeCare Emergency, Cardiac & Multi-Speciality Hospital",
        "name": "LifeCare Emergency & Cardiac Hospital",
        "localized_name": {
            "mr-IN": "लाईफकेअर इमर्जन्सी व मल्टिस्पेशालिटी हॉस्पिटल",
            "hi-IN": "लाइफकेयर इमरजेंसी एवं कार्डियक अस्पताल",
            "en-IN": "LifeCare Emergency & Cardiac Hospital"
        },
        "facility_type": FacilityTypeEnum.SPECIALIZED_HOSPITAL,
        "ownership": FacilityOwnershipEnum.PRIVATE_EMPANELLED,
        "authority": "NABH Accredited Empanelled Facility",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Taluka",
        "village": "Highway Junction",
        "pincode": "415003",
        "address": "National Highway 4 Bypass, Near Kalyanpur Toll Plaza",
        "landmark": "Near Hotel Sahyadri Junction",
        "latitude": 18.5900,
        "longitude": 73.9200, # ~14.5 km
        "phone": "+91 2162 289000",
        "email": "emergency@lifecarehospital.org",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "PVT_NABH_REG_9921",
        "source_name": "NABH & PM-JAY Empanelled Portal",
        "last_verified_at": datetime(2026, 8, 26, 11, 30, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "00:00", "closing_time": "23:59", "is_24x7_emergency": True, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "EMERGENCY_24X7",
                "localized_service_name": {"mr-IN": "२४x७ कार्डियाक कॅथलॅब, स्ट्रोक व अतिदक्षता विभाग (ICU)", "hi-IN": "24x7 हृदय व आपातकालीन आईसीयू", "en-IN": "24x7 Cardiac Cath Lab, Stroke Unit, Advanced ICU"},
                "service_level": "TERTIARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "SCHEME_CASHLESS"
            },
            {
                "service_code": "PATHOLOGY_XRAY",
                "localized_service_name": {"mr-IN": "२४ तास सीटी अँजिओग्राफी व 2D इको", "hi-IN": "24 घंटे सीटी एंजियोग्राफी व इको", "en-IN": "24x7 CT Angiography, 2D Echo, Cardiac Biomarkers"},
                "service_level": "TERTIARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "SCHEME_CASHLESS"
            }
        ],
        "schemes": [
            {"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat PM-JAY (Cardiology & Trauma Empanelled)", "empanelment_reference": "NHA-PVT-LC-4421", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "PM-JAY Hospital Search Portal"},
            {"scheme_code": "MJPJAY", "scheme_name": "Mahatma Jyotirao Phule Jan Arogya Yojana (Cardiac Surgery)", "empanelment_reference": "MJPJAY-PVT-LC-4421", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "SHAS Maharashtra"}
        ]
    },
    {
        "public_reference": "FAC-2026-006",
        "code": "PVT-MATSYA-MAT-01",
        "official_name": "Vatsalya Mother & Child Speciality Hospital",
        "name": "Vatsalya Mother & Child Hospital",
        "localized_name": {
            "mr-IN": "वात्सल्य माता व बाल रुग्णालय (NICU सुविधा)",
            "hi-IN": "वात्सल्य मातृ एवं शिशु अस्पताल",
            "en-IN": "Vatsalya Mother & Child Speciality Hospital"
        },
        "facility_type": FacilityTypeEnum.SPECIALIZED_HOSPITAL,
        "ownership": FacilityOwnershipEnum.PRIVATE_EMPANELLED,
        "authority": "District Health Authority Registered",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Taluka",
        "village": "Taluka Extension",
        "pincode": "415002",
        "address": "Station Road, Opp Mahila Bachat Bhavan, Kalyanpur",
        "landmark": "Opposite Taluka Girls High School",
        "latitude": 18.5700,
        "longitude": 73.9100, # ~11.2 km
        "phone": "+91 2162 265432",
        "email": "care@vatsalyamaternity.com",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "PVT_MAT_REG_7712",
        "source_name": "District Health Department Registry",
        "last_verified_at": datetime(2026, 8, 25, 16, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "00:00", "closing_time": "23:59", "is_24x7_emergency": True, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "MATERNITY_DELIVERY",
                "localized_service_name": {"mr-IN": "२४x७ स्त्रीरोग तज्ज्ञ, सिझेरियन प्रसूती व एनआयसीयू", "hi-IN": "24x7 स्त्रीरोग विशेषज्ञ व सुरक्षित प्रसव", "en-IN": "24x7 Obstetrician on-duty, Advanced C-Section & NICU Incubators"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": True,
                "appointment_requirement": False,
                "cost_type": "SCHEME_CASHLESS"
            },
            {
                "service_code": "CHILD_VACCINATION",
                "localized_service_name": {"mr-IN": "बालरोग तज्ज्ञ तपासणी व नवजात काळजी", "hi-IN": "शिशु रोग विशेषज्ञ देखभाल", "en-IN": "Pediatrician Consultation & Newborn Vaccination"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat PM-JAY (Obstetrics & Neonatal)", "empanelment_reference": "NHA-PVT-VAT-883", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "PM-JAY Official Portal"}
        ]
    },
    {
        "public_reference": "FAC-2026-007",
        "code": "GOVT-CHILD-NUTR-01",
        "official_name": "Kalyanpur Child Immunization & Nutrition Resource Centre",
        "name": "Kalyanpur Child Immunization Centre",
        "localized_name": {
            "mr-IN": "कल्याणपूर बाल लसीकरण व पोषण केंद्र",
            "hi-IN": "कल्याणपुर बाल टीकाकरण केंद्र",
            "en-IN": "Kalyanpur Child Immunization Centre"
        },
        "facility_type": FacilityTypeEnum.PHC,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "ICDS & Health Dept, Maharashtra",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Kalyanpur East",
        "pincode": "415001",
        "address": "East Ward, Behind Anganwadi Central Hub",
        "landmark": "Near Kalyanpur Water Tank",
        "latitude": 18.5350,
        "longitude": 73.8750, # ~3.5 km
        "phone": "+91 2162 234900",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "ICDS_HEALTH_2026_09",
        "source_name": "State ICDS & Universal Immunization Registry",
        "last_verified_at": datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "MONDAY", "opening_time": "09:00", "closing_time": "16:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "TUESDAY", "opening_time": "09:00", "closing_time": "16:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "WEDNESDAY", "opening_time": "09:00", "closing_time": "16:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "THURSDAY", "opening_time": "09:00", "closing_time": "16:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "FRIDAY", "opening_time": "09:00", "closing_time": "16:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "SATURDAY", "opening_time": "09:00", "closing_time": "13:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "CHILD_VACCINATION",
                "localized_service_name": {"mr-IN": "दैनिक सर्व बाल लसीकरण (BCG, Polio, Pentavalent, MR)", "hi-IN": "दैनिक सम्पूर्ण बाल टीकाकरण", "en-IN": "Daily Routine Pediatric Immunization (UIP & Cold Chain Verified)"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {"scheme_code": "RBSK", "scheme_name": "Rashtriya Bal Swasthya Karyakram (RBSK Child Screening)", "empanelment_reference": "RBSK-KALYANPUR-01", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHM Maharashtra"}
        ]
    },
    {
        "public_reference": "FAC-2026-008",
        "code": "DIAG-CENTRAL-LAB-01",
        "official_name": "Central Diagnostic & Pathology Centre Kalyanpur",
        "name": "Kalyanpur Diagnostic & Pathology Lab",
        "localized_name": {
            "mr-IN": "कल्याणपूर केंद्रीय निदान व पॅथॉलॉजी लॅब",
            "hi-IN": "कल्याणपुर डायग्नोस्टिक व पैथोलॉजी लैब",
            "en-IN": "Kalyanpur Central Diagnostic & Pathology Lab"
        },
        "facility_type": FacilityTypeEnum.DIAGNOSTIC_CENTRE,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "Public Health Department PPP Lab",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Kalyanpur",
        "pincode": "415001",
        "address": "Block Health Office Complex, Station Link Road",
        "landmark": "Beside Sub-Divisional Agriculture Office",
        "latitude": 18.5400,
        "longitude": 73.8800, # ~4.0 km
        "phone": "+91 2162 239888",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "GOVT_PPP_LAB_415001",
        "source_name": "Directorate of Health Services Lab Network",
        "last_verified_at": datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "08:00", "closing_time": "20:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "PATHOLOGY_XRAY",
                "localized_service_name": {"mr-IN": "डिजिटल एक्स-रे, रक्त तपासणी, सोनोग्राफी", "hi-IN": "डिजिटल एक्स-रे, रक्त परीक्षण, सोनोग्राफी", "en-IN": "Digital X-Ray, Biochemistry, Ultrasound & Rapid Blood Profiles"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": True,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat Diagnostic Empanelment", "empanelment_reference": "NHA-DIAG-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHA Portal"}
        ]
    },
    {
        "public_reference": "FAC-2026-009",
        "code": "TB-DISTRICT-CHEST-01",
        "official_name": "Taluka TB DOTS & Chest Clinic Kalyanpur",
        "name": "Kalyanpur TB & Chest Disease Centre",
        "localized_name": {
            "mr-IN": "कल्याणपूर तालुका टीबी केंद्र व छातीचे आजार क्लिनिक",
            "hi-IN": "कल्याणपुर टीबी व श्वसन रोग केंद्र",
            "en-IN": "Kalyanpur TB & Chest Disease Centre"
        },
        "facility_type": FacilityTypeEnum.TB_NCD_CENTRE,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "National Tuberculosis Elimination Program (NTEP)",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Kalyanpur West",
        "pincode": "415001",
        "address": "Old Hospital Campus, Kalyanpur West",
        "landmark": "Near Red Cross Bhavan",
        "latitude": 18.5550,
        "longitude": 73.8900, # ~7.0 km
        "phone": "+91 2162 231122",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "NTEP_TB_UNIT_415001",
        "source_name": "Nikshay Central TB Registry",
        "last_verified_at": datetime(2026, 8, 25, 11, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "09:00", "closing_time": "17:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "TB_DOTS",
                "localized_service_name": {"mr-IN": "सीबी-नॅट (CB-NAAT) थुंकी तपासणी व मोफत निक्षय औषधे", "hi-IN": "सीबी-नैट बलगम जांच व टीबी दवा", "en-IN": "CB-NAAT Molecular TB Testing, Sputum Microscopy & Free DOTS"},
                "service_level": "SECONDARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {"scheme_code": "NIKSHAY", "scheme_name": "Nikshay Poshan Yojana (Direct Benefit Transfer)", "empanelment_reference": "NTEP-NIKSHAY-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "Nikshay Portal"}
        ]
    },
    {
        "public_reference": "FAC-2026-010",
        "code": "CSC-AYUSHMAN-01",
        "official_name": "Aaple Sarkar Seva Kendra & Ayushman Bharat Scheme Desk",
        "name": "Kalyanpur CSC & Scheme Help Desk",
        "localized_name": {
            "mr-IN": "आपले सरकार सेवा केंद्र व आयुष्मान भारत मदत कक्ष",
            "hi-IN": "आपले सरकार केंद्र व आयुष्मान हेल्प डेस्क",
            "en-IN": "Kalyanpur CSC & Ayushman Scheme Help Desk"
        },
        "facility_type": FacilityTypeEnum.AYUSHMAN_HELP_DESK,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "Maharashtra IT Corporation & NHA CSC",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Kalyanpur",
        "pincode": "415001",
        "address": "Gram Panchayat Building Ground Floor, Kalyanpur",
        "landmark": "Opposite Gram Panchayat Office",
        "latitude": 18.5250,
        "longitude": 73.8650, # ~0.6 km
        "phone": "+91 98220 12345",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "CSC_VLE_MAHA_1092",
        "source_name": "CSC e-Governance Services India",
        "last_verified_at": datetime(2026, 8, 26, 8, 30, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "MONDAY", "opening_time": "09:30", "closing_time": "18:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "TUESDAY", "opening_time": "09:30", "closing_time": "18:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "WEDNESDAY", "opening_time": "09:30", "closing_time": "18:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "THURSDAY", "opening_time": "09:30", "closing_time": "18:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "FRIDAY", "opening_time": "09:30", "closing_time": "18:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED},
            {"day_of_week": "SATURDAY", "opening_time": "09:30", "closing_time": "18:00", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "AYUSHMAN_HELP_DESK",
                "localized_service_name": {"mr-IN": "आयुष्मान कार्ड e-KYC, डाऊनलोड व योजना मदत", "hi-IN": "आयुष्मान कार्ड e-KYC व प्रिंटिंग", "en-IN": "Ayushman PVC Card e-KYC, PMMVY Online Application, Scheme Seeding"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "FREE"
            }
        ],
        "schemes": [
            {"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat e-KYC & Card Issuance Desk", "empanelment_reference": "CSC-PMJAY-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "NHA Portal"},
            {"scheme_code": "PMMVY", "scheme_name": "PMMVY Online Application Processing", "empanelment_reference": "CSC-PMMVY-09", "verification_status": VerificationStatusEnum.VERIFIED, "official_source": "WCD Portal"}
        ]
    },
    {
        "public_reference": "FAC-2026-011",
        "code": "PHARM-JAN-AUSHADHI-01",
        "official_name": "Pradhan Mantri Bhartiya Jan Aushadhi Kendra (Kalyanpur)",
        "name": "Jan Aushadhi Kendra Kalyanpur",
        "localized_name": {
            "mr-IN": "प्रधानमंत्री भारतीय जन औषधी केंद्र (कल्याणपूर)",
            "hi-IN": "प्रधानमंत्री भारतीय जन औषधि केंद्र",
            "en-IN": "Pradhan Mantri Jan Aushadhi Kendra (Kalyanpur)"
        },
        "facility_type": FacilityTypeEnum.PHARMACY,
        "ownership": FacilityOwnershipEnum.GOVERNMENT,
        "authority": "Pharmaceuticals & Medical Devices Bureau of India (PMBI)",
        "state": "Maharashtra",
        "district": "District 04",
        "block": "Kalyanpur Block",
        "village": "Kalyanpur",
        "pincode": "415001",
        "address": "Shop No 4, Municipal Shopping Complex, ST Stand Road",
        "landmark": "Near ST Stand Entrance",
        "latitude": 18.5280,
        "longitude": 73.8680, # ~2.5 km
        "phone": "+91 94230 55667",
        "verification_status": VerificationStatusEnum.VERIFIED,
        "source_id": "PMBI_JAK_KALYANPUR_01",
        "source_name": "PMBI National Pharmacy Portal",
        "last_verified_at": datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc),
        "hours": [
            {"day_of_week": "ALL_DAYS", "opening_time": "08:30", "closing_time": "21:30", "is_24x7_emergency": False, "verification_status": VerificationStatusEnum.VERIFIED}
        ],
        "services": [
            {
                "service_code": "PHARMACY",
                "localized_service_name": {"mr-IN": "सर्व आवश्यक जेनेरिक औषधे व सर्जिकल साहित्य (५०-९०% स्वस्त)", "hi-IN": "सस्ती जेनेरिक दवाइयां", "en-IN": "Essential Generic Medicines, BP/Sugar Kits, Inhalers, Antibiotics (50-90% Discount)"},
                "service_level": "PRIMARY",
                "availability_status": ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE,
                "emergency_capability": False,
                "appointment_requirement": False,
                "cost_type": "SUBSIDIZED"
            }
        ],
        "schemes": []
    }
]

def seed_facilities_data(db: Session) -> int:
    """
    Seeds facilities, services, operating hours, and scheme empanelments.
    Completely idempotent: checks by public_reference or code and updates or inserts without creating duplicates.
    """
    created_or_updated = 0

    for fac_data in DEMO_FACILITIES:
        fac = db.query(Facility).filter(
            (Facility.public_reference == fac_data["public_reference"]) |
            (Facility.code == fac_data["code"])
        ).first()

        if not fac:
            fac = Facility(
                public_reference=fac_data["public_reference"],
                code=fac_data["code"],
                official_name=fac_data["official_name"],
                name=fac_data.get("name", fac_data["official_name"]),
                localized_name=fac_data["localized_name"],
                facility_type=fac_data["facility_type"],
                ownership=fac_data["ownership"],
                authority=fac_data["authority"],
                state=fac_data["state"],
                district=fac_data["district"],
                district_name=fac_data["district"],
                block=fac_data["block"],
                block_name=fac_data["block"],
                village=fac_data.get("village"),
                pincode=fac_data.get("pincode"),
                address=fac_data.get("address"),
                landmark=fac_data.get("landmark"),
                latitude=fac_data["latitude"],
                longitude=fac_data["longitude"],
                phone=fac_data.get("phone"),
                email=fac_data.get("email"),
                verification_status=fac_data["verification_status"],
                source_id=fac_data["source_id"],
                source_name=fac_data["source_name"],
                last_verified_at=fac_data["last_verified_at"],
                is_active=True
            )
            db.add(fac)
            db.flush()
            created_or_updated += 1
        else:
            # Update fields to ensure latest verified demo state
            fac.official_name = fac_data["official_name"]
            fac.name = fac_data.get("name", fac_data["official_name"])
            fac.localized_name = fac_data["localized_name"]
            fac.facility_type = fac_data["facility_type"]
            fac.ownership = fac_data["ownership"]
            fac.authority = fac_data["authority"]
            fac.latitude = fac_data["latitude"]
            fac.longitude = fac_data["longitude"]
            fac.phone = fac_data.get("phone")
            fac.email = fac_data.get("email")
            fac.address = fac_data.get("address")
            fac.landmark = fac_data.get("landmark")
            fac.pincode = fac_data.get("pincode")
            fac.verification_status = fac_data["verification_status"]
            fac.last_verified_at = fac_data["last_verified_at"]
            db.flush()

        # Seed hours idempotently
        for hr_data in fac_data.get("hours", []):
            existing_hour = db.query(FacilityHours).filter(
                FacilityHours.facility_id == fac.id,
                FacilityHours.day_of_week == hr_data["day_of_week"]
            ).first()
            if not existing_hour:
                db.add(FacilityHours(
                    facility_id=fac.id,
                    day_of_week=hr_data["day_of_week"],
                    opening_time=hr_data.get("opening_time"),
                    closing_time=hr_data.get("closing_time"),
                    is_24x7_emergency=hr_data.get("is_24x7_emergency", False),
                    verification_status=hr_data.get("verification_status", VerificationStatusEnum.VERIFIED),
                    last_verified_at=fac_data["last_verified_at"]
                ))
            else:
                existing_hour.opening_time = hr_data.get("opening_time")
                existing_hour.closing_time = hr_data.get("closing_time")
                existing_hour.is_24x7_emergency = hr_data.get("is_24x7_emergency", False)

        # Seed services idempotently
        for srv_data in fac_data.get("services", []):
            existing_srv = db.query(FacilityService).filter(
                FacilityService.facility_id == fac.id,
                FacilityService.service_code == srv_data["service_code"]
            ).first()
            if not existing_srv:
                db.add(FacilityService(
                    facility_id=fac.id,
                    service_code=srv_data["service_code"],
                    localized_service_name=srv_data["localized_service_name"],
                    service_level=srv_data.get("service_level", "PRIMARY"),
                    availability_status=srv_data.get("availability_status", ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE),
                    emergency_capability=srv_data.get("emergency_capability", False),
                    appointment_requirement=srv_data.get("appointment_requirement", False),
                    cost_type=srv_data.get("cost_type", "FREE"),
                    last_verified_at=fac_data["last_verified_at"]
                ))
            else:
                existing_srv.localized_service_name = srv_data["localized_service_name"]
                existing_srv.service_level = srv_data.get("service_level", "PRIMARY")
                existing_srv.availability_status = srv_data.get("availability_status", ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE)
                existing_srv.emergency_capability = srv_data.get("emergency_capability", False)
                existing_srv.appointment_requirement = srv_data.get("appointment_requirement", False)
                existing_srv.cost_type = srv_data.get("cost_type", "FREE")

        # Seed schemes idempotently
        for sch_data in fac_data.get("schemes", []):
            existing_sch = db.query(FacilitySchemeEmpanelment).filter(
                FacilitySchemeEmpanelment.facility_id == fac.id,
                FacilitySchemeEmpanelment.scheme_code == sch_data["scheme_code"]
            ).first()
            if not existing_sch:
                db.add(FacilitySchemeEmpanelment(
                    facility_id=fac.id,
                    scheme_code=sch_data["scheme_code"],
                    scheme_name=sch_data["scheme_name"],
                    empanelment_reference=sch_data.get("empanelment_reference"),
                    verification_status=sch_data.get("verification_status", VerificationStatusEnum.VERIFIED),
                    official_source=sch_data.get("official_source", "State Health Agency"),
                    last_verified_at=fac_data["last_verified_at"]
                ))
            else:
                existing_sch.scheme_name = sch_data["scheme_name"]
                existing_sch.empanelment_reference = sch_data.get("empanelment_reference")
                existing_sch.verification_status = sch_data.get("verification_status", VerificationStatusEnum.VERIFIED)

    db.commit()
    logger.info(f"Successfully seeded {len(DEMO_FACILITIES)} facilities idempotently.")
    return len(DEMO_FACILITIES)

if __name__ == "__main__":
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        count = seed_facilities_data(db)
        print(f"Seeded {count} facilities successfully.")
    finally:
        db.close()
