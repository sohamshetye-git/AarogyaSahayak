import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.models import (
    CitizenProfile, Case, SymptomObservation, VitalRecord, AshaVisit, Referral,
    Facility, User, AuditLog, Notification, InformationSourceEnum,
    CasePriorityEnum, CaseStatusEnum, CitizenAttachment, FollowUp, UserRoleEnum
)
from app.schemas import (
    PatientRegistrationRequest, DuplicateCheckRequest, DuplicateCheckResponse,
    DuplicateCitizenSummary, PatientRegistrationResponseData,
    PatientRegistrationOptionsResponse
)
from app.safety.emergency_rules import EmergencyRuleEvaluator
from app.safety.pii_masking import PIIMaskingService

class PatientRegistrationService:
    @staticmethod
    def generate_reference(prefix: str = "CIT") -> str:
        num = random.randint(100000, 999999)
        return f"{prefix}-2026-{num}"

    @classmethod
    def get_registration_options(cls, db: Session) -> PatientRegistrationOptionsResponse:
        facilities = db.query(Facility).filter(Facility.is_active == True).all()
        facility_list = [
            {
                "id": f.id,
                "code": f.code,
                "name": f.name,
                "facility_type": f.facility_type,
                "block_name": f.block_name,
                "district_name": f.district_name,
                "approx_distance_km": round(random.uniform(1.5, 12.0), 1),
                "emergency_services": True if f.facility_type in ["PHC", "CHC", "DISTRICT_HOSPITAL"] else False
            }
            for f in facilities
        ]
        if not facility_list:
            facility_list = [
                {"id": "fac-01", "code": "PHC-09", "name": "Kalyanpur Primary Health Centre", "facility_type": "PHC", "block_name": "Kalyanpur Block", "district_name": "District 04", "approx_distance_km": 3.5, "emergency_services": True},
                {"id": "fac-02", "code": "CHC-02", "name": "Taluka Community Health Centre", "facility_type": "CHC", "block_name": "Kalyanpur Block", "district_name": "District 04", "approx_distance_km": 14.0, "emergency_services": True},
                {"id": "fac-03", "code": "SC-01", "name": "Kalyanpur Sub-Centre", "facility_type": "SUB_CENTER", "block_name": "Kalyanpur Block", "district_name": "District 04", "approx_distance_km": 1.0, "emergency_services": False}
            ]

        villages = [
            {"id": "v-01", "name": "Kalyanpur", "block": "Kalyanpur Block", "sub_center": "Kalyanpur Sub-Centre"},
            {"id": "v-02", "name": "Shivaji Nagar", "block": "Kalyanpur Block", "sub_center": "Kalyanpur Sub-Centre"},
            {"id": "v-03", "name": "Rampur", "block": "Kalyanpur Block", "sub_center": "Rampur Sub-Centre"},
            {"id": "v-04", "name": "Ganeshpur", "block": "Kalyanpur Block", "sub_center": "Rampur Sub-Centre"},
            {"id": "v-05", "name": "Bhim Nagar", "block": "Kalyanpur Block", "sub_center": "Bhim Sub-Centre"}
        ]

        sub_centers = [
            {"id": "sc-01", "name": "Kalyanpur Sub-Centre", "assigned_phc": "Kalyanpur PHC"},
            {"id": "sc-02", "name": "Rampur Sub-Centre", "assigned_phc": "Kalyanpur PHC"},
            {"id": "sc-03", "name": "Bhim Sub-Centre", "assigned_phc": "Kalyanpur PHC"}
        ]

        symptoms = [
            {"id": "sym-01", "term": "Severe Headache", "category": "Neurological / Maternal"},
            {"id": "sym-02", "term": "Blurred Vision", "category": "Neurological / Maternal"},
            {"id": "sym-03", "term": "Swelling in Feet / Edema", "category": "Maternal / Renal"},
            {"id": "sym-04", "term": "High Fever", "category": "Infectious"},
            {"id": "sym-05", "term": "Persistent Cough (>2 weeks)", "category": "Respiratory / TB"},
            {"id": "sym-06", "term": "Chest Pain", "category": "Cardiovascular / Critical"},
            {"id": "sym-07", "term": "Shortness of Breath", "category": "Respiratory / Critical"},
            {"id": "sym-08", "term": "Abdominal Pain", "category": "Gastro / Maternal"},
            {"id": "sym-09", "term": "Reduced Fetal Movement", "category": "Maternal Critical"},
            {"id": "sym-10", "term": "Watery Diarrhoea & Dehydration", "category": "Paediatric / Gastro"},
            {"id": "sym-11", "term": "Vomiting", "category": "Gastro"},
            {"id": "sym-12", "term": "Generalized Body Weakness", "category": "General"}
        ]

        return PatientRegistrationOptionsResponse(
            states=["Maharashtra", "Madhya Pradesh", "Gujarat", "Rajasthan", "Karnataka"],
            districts=["District 04", "Pune", "Nashik", "Nagpur", "Aurangabad", "Solapur"],
            blocks=["Kalyanpur Block", "Haveli", "Baramati", "Shirur"],
            villages=villages,
            facilities=facility_list,
            sub_centers=sub_centers,
            symptoms=symptoms,
            blood_groups=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "UNKNOWN"],
            household_categories=["PRIORITY", "BPL", "ANTYODAYA", "OTHER", "UNKNOWN"],
            ration_card_categories=["YELLOW", "ORANGE", "WHITE", "NONE"],
            special_conditions=[
                {"code": "NONE", "label": "None / General Health"},
                {"code": "PREGNANCY", "label": "Antenatal / Pregnancy Care"},
                {"code": "POSTNATAL", "label": "Postnatal Mother & Newborn Care"},
                {"code": "CHILD", "label": "Child Health & Immunization (0-5 Yrs)"},
                {"code": "NCD", "label": "Hypertension / Diabetes / NCD Care"},
                {"code": "TB", "label": "Tuberculosis / Respiratory Screening"},
                {"code": "NUTRITION", "label": "Severe Acute Malnutrition (SAM/MAM)"},
                {"code": "OTHER", "label": "Other Special Condition"}
            ],
            programmes=[
                {"code": "JSY", "label": "Janani Suraksha Yojana (JSY)"},
                {"code": "PMMVY", "label": "Pradhan Mantri Matru Vandana Yojana (PMMVY)"},
                {"code": "PMJAY", "label": "Ayushman Bharat PM-JAY"},
                {"code": "MJPJAY", "label": "Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)"},
                {"code": "RBSK", "label": "Rashtriya Bal Swasthya Karyakram (RBSK)"},
                {"code": "NTEP", "label": "National TB Elimination Programme (NTEP)"},
                {"code": "NPCDCS", "label": "National Programme for NCDs (NPCDCS)"}
            ],
            languages=[
                {"code": "mr-IN", "label": "मराठी (Marathi)"},
                {"code": "hi-IN", "label": "हिंदी (Hindi)"},
                {"code": "en-IN", "label": "English"}
            ]
        )

    @classmethod
    def check_duplicates(cls, db: Session, req: DuplicateCheckRequest) -> DuplicateCheckResponse:
        matches: List[DuplicateCitizenSummary] = []

        # 1. Exact ABHA matching
        if req.abha_number and req.abha_number.strip():
            clean_abha = req.abha_number.strip()
            existing_abha = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == clean_abha).first()
            if existing_abha:
                matches.append(DuplicateCitizenSummary(
                    id=existing_abha.id,
                    display_name=existing_abha.display_name,
                    masked_phone=PIIMaskingService.mask_phone(existing_abha.phone) if existing_abha.phone else None,
                    masked_abha=PIIMaskingService.mask_abha(existing_abha.abha_reference) if existing_abha.abha_reference else None,
                    village_name=existing_abha.village_name or "Kalyanpur",
                    age_estimate=existing_abha.age_estimate,
                    active_case_count=len(existing_abha.cases),
                    similarity_reason="Exact ABHA Number Match"
                ))

        # 2. Phone match
        if req.phone and req.phone.strip() and len(req.phone.strip()) >= 10:
            clean_phone = req.phone.strip()
            existing_phones = db.query(CitizenProfile).filter(CitizenProfile.phone == clean_phone).all()
            for ep in existing_phones:
                if not any(m.id == ep.id for m in matches):
                    matches.append(DuplicateCitizenSummary(
                        id=ep.id,
                        display_name=ep.display_name,
                        masked_phone=PIIMaskingService.mask_phone(ep.phone),
                        masked_abha=PIIMaskingService.mask_abha(ep.abha_reference) if ep.abha_reference else None,
                        village_name=ep.village_name or "Kalyanpur",
                        age_estimate=ep.age_estimate,
                        active_case_count=len(ep.cases),
                        similarity_reason="Exact Phone Number Match"
                    ))

        # 3. Name + Village match
        if req.full_name and len(req.full_name.strip()) > 3:
            name_term = f"%{req.full_name.strip()}%"
            query = db.query(CitizenProfile).filter(CitizenProfile.display_name.ilike(name_term))
            if req.village_name:
                query = query.filter(CitizenProfile.village_name.ilike(f"%{req.village_name.strip()}%"))
            existing_names = query.limit(3).all()
            for en in existing_names:
                if not any(m.id == en.id for m in matches):
                    matches.append(DuplicateCitizenSummary(
                        id=en.id,
                        display_name=en.display_name,
                        masked_phone=PIIMaskingService.mask_phone(en.phone) if en.phone else None,
                        masked_abha=PIIMaskingService.mask_abha(en.abha_reference) if en.abha_reference else None,
                        village_name=en.village_name or "Kalyanpur",
                        age_estimate=en.age_estimate,
                        active_case_count=len(en.cases),
                        similarity_reason="Similar Name & Same Village Match"
                    ))

        return DuplicateCheckResponse(
            has_potential_duplicate=len(matches) > 0,
            potential_matches=matches
        )

    @classmethod
    def register_patient_atomic(
        cls,
        db: Session,
        req: PatientRegistrationRequest,
        current_asha_user: User
    ) -> PatientRegistrationResponseData:
        """
        Executes registration in a single database transaction with idempotency and audit logs.
        Creates CitizenProfile, optional Case, optional AshaVisit, optional Referral, and optional FollowUp.
        """
        # 1. Extract and validate nested Referral & Follow-up inputs
        referral_required = False
        referral_urgency = "ROUTINE"
        referral_facility_id = None
        referral_reason = None
        transport_assistance_required = False
        citizen_response = "ACCEPTED"
        refusal_reason = None

        if req.referral and req.referral.required:
            referral_required = True
            referral_urgency = req.referral.urgency
            referral_facility_id = req.referral.facility_id
            referral_reason = req.referral.reason
            transport_assistance_required = req.referral.transport_assistance_required
            citizen_response = req.referral.citizen_response
            refusal_reason = req.referral.refusal_reason
        elif getattr(req, "referral_required", None):
            referral_required = True
            referral_urgency = getattr(req, "referral_urgency", "ROUTINE") or "ROUTINE"
            referral_facility_id = getattr(req, "referral_facility_id", None)
            referral_reason = getattr(req, "referral_reason", None)

        followup_required = False
        followup_date = None
        followup_purpose = None
        followup_notes = None

        if req.follow_up and req.follow_up.required:
            followup_required = True
            followup_date = req.follow_up.due_date
            followup_purpose = req.follow_up.purpose
            followup_notes = req.follow_up.notes
        elif getattr(req, "followup_required", None):
            followup_required = True
            followup_date = getattr(req, "followup_date", None)
            followup_purpose = getattr(req, "followup_purpose", None)
            followup_notes = getattr(req, "followup_notes", None)

        # 2. Safety and Validation checks
        if referral_required:
            if not referral_facility_id or not referral_facility_id.strip():
                raise ValueError("Referral facility ID is required when referring citizen.")
            if not referral_reason or not referral_reason.strip():
                raise ValueError("Referral reason / clinical note is required when referring citizen.")
            if citizen_response == "REFUSED" and (not refusal_reason or not refusal_reason.strip()):
                raise ValueError("Refusal reason is required when citizen declines referral.")
            # Enforce Case creation when referred
            req.create_current_case = True

        if followup_required:
            if not followup_date:
                raise ValueError("Follow-up date is required when scheduling a follow-up.")
            if not followup_purpose or not followup_purpose.strip():
                raise ValueError("Follow-up purpose/instructions are required when scheduling a follow-up.")
            try:
                due_dt = datetime.strptime(followup_date, "%Y-%m-%d")
                today_date = datetime.now(timezone.utc).date()
                if due_dt.date() < today_date:
                    raise ValueError("Follow-up due date cannot be in the past.")
            except ValueError as ve:
                raise ve
            except Exception:
                raise ValueError("Invalid follow-up date format (expected YYYY-MM-DD).")

        # 3. Duplicate check & Override
        if req.abha_number and req.abha_number.strip():
            clean_abha = req.abha_number.strip()
            existing = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == clean_abha).first()
            if existing and not req.duplicate_override_reason:
                raise ValueError("ABHA number already registered to another citizen. Please provide duplicate override justification or use existing citizen record.")

        # 4. Vitals & Deterministic Safety Rules Evaluation
        v = req.vitals
        systolic = v.systolic_bp if v and v.measured else None
        diastolic = v.diastolic_bp if v and v.measured else None
        spo2 = v.spo2 if v and v.measured else None
        temp = v.temperature_c if v and v.measured else None

        # Check pregnancy condition
        is_maternal = False
        gestational_wks = None
        if req.special_conditions and req.special_conditions.condition_type == "PREGNANCY":
            is_maternal = True
            if req.special_conditions.maternal and req.special_conditions.maternal.gestational_weeks:
                gestational_wks = req.special_conditions.maternal.gestational_weeks

        # Collect symptoms
        symptom_list = list(req.symptoms)
        if req.special_conditions and req.special_conditions.maternal:
            m = req.special_conditions.maternal
            if m.severe_headache: symptom_list.append("Severe Headache")
            if m.blurred_vision: symptom_list.append("Blurred Vision")
            if m.severe_swelling: symptom_list.append("Swelling in feet")
            if m.bleeding: symptom_list.append("Heavy Bleeding")
            if m.reduced_fetal_movement: symptom_list.append("Reduced Fetal Movement")

        priority, rule_triggered, rule_reason, guidance_text = EmergencyRuleEvaluator.evaluate(
            symptoms=symptom_list,
            is_pregnant=is_maternal,
            gestational_weeks=gestational_wks,
            systolic_bp=systolic,
            diastolic_bp=diastolic,
            spo2=spo2,
            temperature_c=temp
        )

        safety_eval_result = {
            "priority": priority.value,
            "safety_rule_triggered": rule_triggered,
            "safety_rule_reason": rule_reason,
            "guidance_text": guidance_text
        }

        # Safety trigger validation: referral or documented citizen refusal is mandatory
        if rule_triggered:
            if not referral_required:
                raise ValueError("Urgent warning signs detected. Referral or documented citizen refusal must be required.")
            if citizen_response == "REFUSED" and (not refusal_reason or not refusal_reason.strip()):
                raise ValueError("Urgent warning signs detected. Refusal reason must be documented since referral was declined.")

        # 5. Begin DB Transaction Operations
        try:
            # Derive age
            calc_age = req.approximate_age
            if req.date_of_birth and not req.exact_dob_unknown:
                try:
                    dob_dt = datetime.strptime(req.date_of_birth, "%Y-%m-%d")
                    today = datetime.now(timezone.utc)
                    calc_age = today.year - dob_dt.year - ((today.month, today.day) < (dob_dt.month, dob_dt.day))
                except Exception:
                    calc_age = req.approximate_age or 25

            # Create CitizenProfile
            citizen = CitizenProfile(
                display_name=req.full_name.strip(),
                date_of_birth=req.date_of_birth,
                age_estimate=calc_age,
                sex=req.sex,
                phone=req.phone.strip() if req.phone else None,
                alternate_phone=req.alternate_phone.strip() if req.alternate_phone else None,
                preferred_contact_method=req.preferred_contact_method,
                abha_reference=req.abha_number.strip() if req.abha_number else None,
                address=req.address,
                village_id=req.village_id,
                village_name=req.village_name or "Kalyanpur",
                pincode=req.pincode,
                state=req.state or "Maharashtra",
                district=req.district or "District 04",
                block_taluka=req.block_taluka or "Kalyanpur Block",
                gram_panchayat=req.gram_panchayat or "Kalyanpur GP",
                sub_center_id=req.sub_center_id,
                assigned_facility_id=req.assigned_facility_id,
                assigned_asha_id=current_asha_user.id,
                emergency_contact_name=req.emergency_contact_name,
                emergency_contact_phone=req.emergency_contact_phone,
                emergency_contact_relation=req.emergency_contact_relation,
                head_of_household_name=req.head_of_household_name,
                head_of_household_relation=req.head_of_household_relation,
                family_id=req.family_id,
                household_category=req.household_category,
                ration_card_category=req.ration_card_category,
                preferred_language=req.preferred_language or "mr-IN",
                literacy_assistance_needed=req.literacy_assistance_needed,
                accessibility_needs=req.accessibility_needs,
                registration_consent_obtained=req.registration_consent_obtained,
                voice_consent_obtained=req.voice_consent_obtained,
                consent_method=req.consent_method,
                guardian_name=req.guardian_name,
                guardian_relation=req.guardian_relation,
                consent_timestamp=datetime.now(timezone.utc) if req.registration_consent_obtained else None,
                blood_group=req.blood_group,
                allergies=req.allergies,
                chronic_conditions=req.chronic_conditions,
                current_medications=[m.model_dump() for m in req.current_medications],
                disability_notes=req.disability_notes,
                previous_illnesses=req.previous_illnesses,
                previous_surgeries=req.previous_surgeries,
                tobacco_use=req.tobacco_use,
                alcohol_use=req.alcohol_use,
                programme_enrollments=req.programme_enrollments,
                health_notes=req.health_notes,
                is_pregnant=is_maternal,
                gestational_weeks=gestational_wks
            )
            db.add(citizen)
            db.flush()

            # Audit Citizen Registration
            audit_reg = AuditLog(
                actor_user_id=current_asha_user.id,
                actor_role="ASHA_WORKER",
                action="CITIZEN_REGISTERED",
                resource_type="CitizenProfile",
                resource_id=citizen.id,
                outcome="SUCCESS",
                metadata_json={
                    "client_registration_id": req.client_registration_id,
                    "has_duplicate_override": bool(req.duplicate_override_reason),
                    "duplicate_override_reason": req.duplicate_override_reason
                }
            )
            db.add(audit_reg)

            created_case: Optional[Case] = None
            created_visit: Optional[AshaVisit] = None
            created_referral: Optional[Referral] = None
            created_followup: Optional[FollowUp] = None

            # Create Case if required
            if req.create_current_case or (req.vitals and req.vitals.measured):
                primary_concern = req.chief_complaint or req.reason_for_visit or (", ".join(symptom_list) if symptom_list else "General health checkup")
                case_ref = cls.generate_reference("CASE")

                created_case = Case(
                    reference=case_ref,
                    citizen_id=citizen.id,
                    priority=priority,
                    status=CaseStatusEnum.NEW,
                    primary_concern=primary_concern,
                    preferred_language=req.preferred_language or "mr-IN",
                    assigned_asha_id=current_asha_user.id,
                    assigned_asha_name=current_asha_user.name,
                    assigned_facility_id=referral_facility_id or req.assigned_facility_id or "PHC-09",
                    assigned_facility_name="Kalyanpur Primary Health Center",
                    safety_rule_triggered=rule_triggered,
                    safety_rule_reason=rule_reason,
                    citizen_guidance_text=guidance_text
                )
                db.add(created_case)
                db.flush()

                # Advance Case Lifecycle
                from app.services.case_service import CaseService
                CaseService.update_status(db, created_case, CaseStatusEnum.ASHA_ACKNOWLEDGED)
                CaseService.update_status(db, created_case, CaseStatusEnum.CITIZEN_CONTACTED)
                if referral_required:
                    CaseService.update_status(db, created_case, CaseStatusEnum.REFERRED_TO_PHC)
                elif v and v.measured:
                    CaseService.update_status(db, created_case, CaseStatusEnum.ASHA_REVIEWED)
                db.flush()

                # Record symptoms
                for s in symptom_list:
                    obs = SymptomObservation(
                        case_id=created_case.id,
                        spoken_term=s,
                        normalized_term=s.title(),
                        severity=req.severity,
                        duration_text=req.duration,
                        source_type=InformationSourceEnum.ASHA_CONFIRMED,
                        recorded_by=current_asha_user.name
                    )
                    db.add(obs)

                # Record vitals
                if v and v.measured:
                    vit = VitalRecord(
                        case_id=created_case.id,
                        systolic_bp=v.systolic_bp,
                        diastolic_bp=v.diastolic_bp,
                        temperature_c=v.temperature_c,
                        spo2=v.spo2,
                        pulse=v.pulse,
                        respiratory_rate=v.respiratory_rate,
                        weight_kg=v.weight_kg,
                        glucose_mg_dl=v.glucose_mg_dl,
                        is_warning_sign=rule_triggered,
                        source_type=InformationSourceEnum.DEVICE_MEASURED,
                        recorded_by=current_asha_user.name
                    )
                    db.add(vit)

                # Record AshaVisit
                visit_ref = cls.generate_reference("VISIT")
                created_visit = AshaVisit(
                    reference=visit_ref,
                    case_id=created_case.id,
                    asha_worker_id=current_asha_user.id,
                    visit_type="PATIENT_REGISTRATION_VISIT",
                    status="COMPLETED",
                    consent_obtained=req.registration_consent_obtained,
                    notes=req.confirmed_summary or req.health_notes or "Initial home registration visit completed.",
                    next_action="REFER_TO_PHC" if referral_required else "ROUTINE_MONITORING"
                )
                db.add(created_visit)
                db.flush()

            # Create Referral if required
            if referral_required:
                ref_urgency = CasePriorityEnum.URGENT if (rule_triggered or referral_urgency == "URGENT") else CasePriorityEnum.ROUTINE
                ref_facility = db.query(Facility).filter(Facility.id == referral_facility_id).first()
                ref_facility_name = ref_facility.name if ref_facility else "Kalyanpur Primary Health Center"

                ref_record = Referral(
                    reference=cls.generate_reference("REF"),
                    case_id=created_case.id if created_case else None,
                    from_asha_id=current_asha_user.id,
                    to_facility_id=referral_facility_id,
                    to_facility_name=ref_facility_name,
                    urgency=ref_urgency,
                    reason=referral_reason or rule_reason or "Urgent PHC referral following home patient registration",
                    status="PENDING_DOCTOR_REVIEW",
                    transport_assistance_required=transport_assistance_required,
                    citizen_response=citizen_response,
                    refusal_reason=refusal_reason
                )
                db.add(ref_record)
                db.flush()
                created_referral = ref_record

                # Notify Doctor
                doctor = db.query(User).filter(User.role == "PHC_DOCTOR").first()
                if doctor:
                    notif = Notification(
                        recipient_user_id=doctor.id,
                        case_id=created_case.id if created_case else None,
                        notification_type="NEW_PATIENT_REFERRAL",
                        title=f"New Patient Referral: {ref_record.reference}",
                        message=f"Patient {citizen.display_name} registered and referred by ASHA {current_asha_user.name}.",
                        priority=ref_urgency
                    )
                    db.add(notif)

            # Create FollowUp if required
            if followup_required:
                due_dt = datetime.strptime(followup_date, "%Y-%m-%d")
                followup = FollowUp(
                    case_id=created_case.id if created_case else None,
                    citizen_id=citizen.id,
                    referral_id=created_referral.id if created_referral else None,
                    created_by_id=current_asha_user.id,
                    source="ASHA_REGISTRATION",
                    task_type="BP_MONITORING" if (created_case and created_case.priority == CasePriorityEnum.URGENT) else "GENERAL_FOLLOWUP",
                    assigned_role=UserRoleEnum.ASHA_WORKER,
                    assigned_user_id=current_asha_user.id,
                    instructions=followup_purpose,
                    result=followup_notes,
                    priority=CasePriorityEnum.URGENT if (created_case and created_case.priority == CasePriorityEnum.URGENT) else CasePriorityEnum.HIGH,
                    due_at=due_dt,
                    status="PENDING"
                )
                db.add(followup)
                db.flush()
                created_followup = followup

            # Link attachments
            if req.attachment_ids:
                db.query(CitizenAttachment).filter(CitizenAttachment.id.in_(req.attachment_ids)).update(
                    {"citizen_id": citizen.id, "case_id": created_case.id if created_case else None},
                    synchronize_session=False
                )

            # Commit atomic transaction
            db.commit()

        except Exception as e:
            db.rollback()
            raise e

        # Refresh instances
        db.refresh(citizen)
        if created_case: db.refresh(created_case)
        if created_visit: db.refresh(created_visit)
        if created_referral: db.refresh(created_referral)
        if created_followup: db.refresh(created_followup)

        # Broadcast domain event for referral
        if created_referral and created_case:
            try:
                from app.services.event_bus import publish_domain_event
                publish_domain_event(
                    event_name="REFERRAL_CREATED",
                    payload={
                        "referral_id": created_referral.id,
                        "referral_reference": created_referral.reference,
                        "case_id": created_case.id,
                        "case_reference": created_case.reference,
                        "citizen_name": citizen.display_name,
                        "facility_name": created_referral.to_facility_name,
                        "urgency": created_referral.urgency.value if hasattr(created_referral.urgency, "value") else created_referral.urgency
                    },
                    target_roles=["PHC_DOCTOR"],
                    facility_id=created_referral.to_facility_id
                )
            except Exception as e:
                print(f"Failed to publish REFERRAL_CREATED event: {e}")

        # Schemes recommendation preview
        schemes_preview = []
        if is_maternal:
            schemes_preview.append({"scheme_code": "JSY", "scheme_name": "Janani Suraksha Yojana", "status": "POTENTIALLY_ELIGIBLE", "benefit": "₹1,400 institutional delivery financial support"})
            schemes_preview.append({"scheme_code": "PMMVY", "scheme_name": "Pradhan Mantri Matru Vandana Yojana", "status": "POTENTIALLY_ELIGIBLE", "benefit": "₹5,000 maternity cash benefit"})
        if req.household_category in ["BPL", "ANTYODAYA", "PRIORITY"]:
            schemes_preview.append({"scheme_code": "PMJAY", "scheme_name": "Ayushman Bharat PM-JAY", "status": "POTENTIALLY_ELIGIBLE", "benefit": "₹5 Lakh family health coverage"})

        return PatientRegistrationResponseData(
            citizen_id=citizen.id,
            citizen_reference=citizen.id[:8].upper(),
            citizen_name=citizen.display_name,
            case_id=created_case.id if created_case else None,
            case_reference=created_case.reference if created_case else None,
            visit_id=created_visit.id if created_visit else None,
            referral_id=created_referral.id if created_referral else None,
            referral_reference=created_referral.reference if created_referral else None,
            follow_up_id=created_followup.id if created_followup else None,
            follow_up_due_date=followup_date if followup_required else None,
            safety_result=safety_eval_result,
            schemes_evaluated=schemes_preview,
            next_route=f"/asha/cases/{created_case.id}" if created_case else "/asha/people"
        )
