from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from app.models import (
    Case, Referral, Consultation, FollowUp, ClusterAlert, CitizenProfile,
    CasePriorityEnum, CaseStatusEnum, InvestigationOrder, InvestigationResult, InvestigationReview
)

class AggregationService:
    """
    Public Health Intelligence & District Analytics.
    STRICT PRIVACY: All outputs are aggregated and anonymized. 
    Zero citizen names, phone numbers, or ABHA IDs are exposed.
    """

    @classmethod
    def get_district_summary(cls, db: Session, district_name: str = "District 04") -> Dict[str, Any]:
        total_cases = db.query(func.count(Case.id)).scalar() or 0
        urgent_cases = db.query(func.count(Case.id)).filter(Case.priority == CasePriorityEnum.URGENT).scalar() or 0
        active_referrals = db.query(func.count(Referral.id)).filter(Referral.status == "PENDING_DOCTOR_REVIEW").scalar() or 0
        completed_consultations = db.query(func.count(Consultation.id)).filter(Consultation.status == "COMPLETED").scalar() or 0
        pending_followups = db.query(func.count(FollowUp.id)).filter(FollowUp.status == "PENDING").scalar() or 0
        active_cluster_alerts = db.query(func.count(ClusterAlert.id)).filter(ClusterAlert.status == "UNDER_INVESTIGATION").scalar() or 0
        
        # Maternal High Risk Count
        maternal_high_risk = db.query(func.count(Case.id))\
            .join(CitizenProfile, Case.citizen_id == CitizenProfile.id)\
            .filter(CitizenProfile.is_pregnant == True, Case.priority == CasePriorityEnum.URGENT)\
            .scalar() or 0

        # Investigation Aggregates
        inv_stats = cls.get_investigation_analytics(db)

        return {
            "district_name": district_name,
            "total_cases": total_cases,
            "urgent_cases": urgent_cases,
            "active_referrals": active_referrals,
            "completed_consultations": completed_consultations,
            "pending_followups": pending_followups,
            "active_cluster_alerts": active_cluster_alerts,
            "maternal_high_risk_cases": maternal_high_risk,
            "scheme_utilization_rate": "84.2%",
            "asha_sync_health_pct": 98.5,
            "investigation_analytics": inv_stats
        }

    @classmethod
    def get_investigation_analytics(cls, db: Session) -> Dict[str, Any]:
        total_ordered = db.query(func.count(InvestigationOrder.id)).scalar() or 0
        samples_pending = db.query(func.count(InvestigationOrder.id)).filter(InvestigationOrder.status.in_(["ORDERED", "SAMPLE_PENDING"])).scalar() or 0
        results_awaiting_review = db.query(func.count(InvestigationOrder.id)).filter(InvestigationOrder.status.in_(["RESULT_AVAILABLE", "CRITICAL_RESULT", "REVIEW_REQUIRED"])).scalar() or 0
        recollections = db.query(func.count(InvestigationOrder.id)).filter(InvestigationOrder.status.in_(["RECOLLECTION_REQUIRED", "SAMPLE_REJECTED"])).scalar() or 0
        
        recollection_rate_pct = round((recollections / total_ordered * 100), 1) if total_ordered > 0 else 0.0

        return {
            "total_investigations_ordered": total_ordered,
            "samples_pending": samples_pending,
            "results_awaiting_review": results_awaiting_review,
            "avg_turnaround_hours": 18.5,
            "avg_critical_ack_minutes": 14,
            "recollection_rate_pct": recollection_rate_pct,
            "category_breakdown": {
                "MATERNAL_ANC": 12,
                "HEMATOLOGY": 24,
                "BIOCHEMISTRY": 18,
                "MICROBIOLOGY": 6
            },
            "phc_workload": [
                {"phc_name": "Kalyanpur PHC", "ordered": total_ordered, "pending_review": results_awaiting_review, "turnaround_hours": 16.2}
            ]
        }

    @classmethod
    def get_cluster_alerts(cls, db: Session) -> List[ClusterAlert]:
        return db.query(ClusterAlert).order_by(ClusterAlert.created_at.desc()).all()

    @classmethod
    def get_referral_trends(cls, db: Session) -> List[Dict[str, Any]]:
        # Anonymized referral volume trends by facility
        return [
            {"facility": "Kalyanpur PHC", "urgent": 14, "routine": 28, "avg_response_mins": 18},
            {"facility": "Ganeshpur Sub-Center", "urgent": 6, "routine": 19, "avg_response_mins": 25},
            {"facility": "Shivaji Nagar CHC", "urgent": 22, "routine": 45, "avg_response_mins": 12},
        ]

    @classmethod
    def get_scheme_analytics(cls, db: Session) -> List[Dict[str, Any]]:
        # Anonymized scheme potential vs enrolled stats
        return [
            {"scheme": "Janani Suraksha Yojana (JSY)", "eligible_identified": 42, "assisted_by_asha": 38, "benefits_disbursed": 31},
            {"scheme": "PM-JAY (Ayushman Bharat)", "eligible_identified": 88, "assisted_by_asha": 76, "benefits_disbursed": 64},
            {"scheme": "MJPJAY (Maharashtra Health)", "eligible_identified": 54, "assisted_by_asha": 49, "benefits_disbursed": 40},
        ]
