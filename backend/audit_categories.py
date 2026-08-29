import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models import SchemeModel, SchemeVersionModel

db = SessionLocal()
schemes = db.query(SchemeModel).all()

categories_meta = [
    {
        "category_id": "maternal_health",
        "category_code": "maternal_health",
        "translated_name": "गरोदरपण आणि मातृत्व",
        "translated_description": "गरोदर मातांसाठी रोख मदत, मोफत तपासणी व पोषण",
        "title_en": "Pregnancy & Maternity",
        "title_hi": "गर्भावस्था और मातृत्व",
        "title_mr": "गरोदरपण आणि मातृत्व",
        "icon": "Baby",
        "keywords": ["maternal_health", "pregnancy", "antenatal_care", "infant", "institutional_delivery"]
    },
    {
        "category_id": "child_health",
        "category_code": "child_health",
        "translated_name": "बाल आरोग्य व लसीकरण",
        "translated_description": "लसीकरण, नवजात शिशु उपचार व मोफत तपासणी",
        "title_en": "Child Health & Vaccination",
        "title_hi": "बाल स्वास्थ्य और टीकाकरण",
        "title_mr": "बाल आरोग्य व लसीकरण",
        "icon": "HeartHandshake",
        "keywords": ["child_health", "immunization", "newborn", "early_intervention"]
    },
    {
        "category_id": "hospitalization",
        "category_code": "hospitalization",
        "translated_name": "मोफत रुग्णालय उपचार",
        "translated_description": "आयुष्मान भारत व महात्मा फुले योजनेतून 5 लाखांपर्यंत कॅशलेस उपचार",
        "title_en": "Hospital Treatment / Assurance",
        "title_hi": "मुफ्त अस्पताल उपचार",
        "title_mr": "मोफत रुग्णालय उपचार",
        "icon": "ShieldCheck",
        "keywords": ["hospitalization", "secondary_care", "tertiary_care", "hospital_access"]
    },
    {
        "category_id": "medicines",
        "category_code": "medicines",
        "translated_name": "औषधे व मोफत तपासण्या",
        "translated_description": "जन औषधी केंद्र व मोफत सरकारी रक्त/लघवी तपासण्या",
        "title_en": "Medicines & Diagnostics",
        "title_hi": "दवाइयाँ और मुफ्त जाँच",
        "title_mr": "औषधे व मोफत तपासण्या",
        "icon": "Pill",
        "keywords": ["medicines", "pharmacy", "diagnosis", "free_diagnosis", "testing"]
    },
    {
        "category_id": "infectious_diseases",
        "category_code": "infectious_diseases",
        "translated_name": "टीबी व संसर्गजन्य आजार",
        "translated_description": "निक्षय पोषण योजना - दरमहा आर्थिक सहाय्य व मोफत औषधे",
        "title_en": "TB & Infectious Diseases",
        "title_hi": "टीबी और संक्रामक रोग",
        "title_mr": "टीबी व संसर्गजन्य आजार",
        "icon": "Activity",
        "keywords": ["infectious_diseases", "tuberculosis", "leprosy", "hiv"]
    },
    {
        "category_id": "ncd",
        "category_code": "ncd",
        "translated_name": "मधुमेह, रक्तदाब व जुनाट आजार",
        "translated_description": "मोफत तपासणी, नियमित औषधोपचार व समुपदेशन",
        "title_en": "Diabetes / BP / NCD",
        "title_hi": "मधुमेह, बीपी और पुरानी बीमारियाँ",
        "title_mr": "मधुमेह, रक्तदाब व जुनाट आजार",
        "icon": "Stethoscope",
        "keywords": ["ncd", "chronic_illness", "diabetes", "cardiovascular", "stroke", "cancer", "dialysis", "kidney_disease", "palliative_care"]
    },
    {
        "category_id": "senior_citizen",
        "category_code": "senior_citizen",
        "translated_name": "ज्येष्ठ नागरिक आरोग्य",
        "translated_description": "मुख्यमंत्री वयोश्री योजना व मोफत वृद्धोपचार",
        "title_en": "Senior-Citizen Care",
        "title_hi": "वरिष्ठ नागरिक स्वास्थ्य",
        "title_mr": "ज्येष्ठ नागरिक आरोग्य",
        "icon": "UserCheck",
        "keywords": ["senior_citizen", "elderly", "geriatric_care"]
    },
    {
        "category_id": "disability",
        "category_code": "disability",
        "translated_name": "दिव्यांग सहाय्य व साधने",
        "translated_description": "सहायक उपकरणे, प्रमाणपत्र व विशेष आरोग्य सवलती",
        "title_en": "Disability Support",
        "title_hi": "दिव्यांग सहायता और उपकरण",
        "title_mr": "दिव्यांग सहाय्य व साधने",
        "icon": "Accessibility",
        "keywords": ["disability", "assistive_devices", "hearing", "rehabilitation"]
    },
    {
        "category_id": "financial_assistance",
        "category_code": "financial_assistance",
        "translated_name": "वैद्यकीय आर्थिक मदत",
        "translated_description": "राष्ट्रीय आरोग्य निधी व धर्मादाय रुग्णालय राखीव खाटा",
        "title_en": "Medical Financial Assistance",
        "title_hi": "चिकित्सा वित्तीय सहायता",
        "title_mr": "वैद्यकीय आर्थिक मदत",
        "icon": "IndianRupee",
        "keywords": ["financial_assistance", "financial_protection", "financial_support", "discretionary_grant", "indigent_patients", "poor_patients", "wage_loss_compensation", "dbt", "affordability"]
    },
    {
        "category_id": "mental_health",
        "category_code": "mental_health",
        "translated_name": "मानसिक आरोग्य व समुपदेशन",
        "translated_description": "टेली-मानस 14416 मोफत 24 तास समुपदेशन",
        "title_en": "Mental Health Services",
        "title_hi": "मानसिक स्वास्थ्य और परामर्श",
        "title_mr": "मानसिक आरोग्य व समुपदेशन",
        "icon": "Smile",
        "keywords": ["mental_health", "tele_counselling"]
    },
    {
        "category_id": "womens_health",
        "category_code": "womens_health",
        "translated_name": "महिला विशेष आरोग्य",
        "translated_description": "कॅन्सर तपासणी, ॲनिमिया मुक्ती व विशेष शिबिरे",
        "title_en": "Women's Health",
        "title_hi": "महिला विशेष स्वास्थ्य",
        "title_mr": "महिला विशेष आरोग्य",
        "icon": "Heart",
        "keywords": ["womens_health", "maternal_health", "cancer", "sickle_cell", "genetic_counselling"]
    },
    {
        "category_id": "public_health",
        "category_code": "public_health",
        "translated_name": "सार्वजनिक आरोग्य सेवा",
        "translated_description": "आयुष्मान आरोग्य मंदिर, प्राथमिक आरोग्य केंद्र व ई-संजीवनी",
        "title_en": "General Public Health",
        "title_hi": "सामान्य सार्वजनिक स्वास्थ्य",
        "title_mr": "सार्वजनिक आरोग्य सेवा",
        "icon": "Building2",
        "keywords": ["public_health", "primary_care", "wellness", "free_services", "free_public_services", "free_treatment", "service_guarantee", "telemedicine", "tribal_health"]
    }
]

print("=== Category DB Audit ===")
for cat in categories_meta:
    matched = []
    for s in schemes:
        sc_cats = s.category_codes or []
        if any(k in sc_cats for k in cat["keywords"]) or cat["category_code"] in sc_cats:
            matched.append(s.scheme_code)
    print(f"Category {cat['category_id']}: count = {len(matched)}, schemes = {matched}")
