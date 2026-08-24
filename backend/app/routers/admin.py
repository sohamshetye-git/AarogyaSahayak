from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import StandardResponse, AdminDashboardResponse, SystemHealthResponse
from app.services.aggregation_service import AggregationService
from app.dependencies import require_admin, require_staff
from app.models import User
from app.config import settings

router = APIRouter(prefix="/admin", tags=["District Health Officer / Admin"])

@router.get("/dashboard", response_model=StandardResponse)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    summary = AggregationService.get_district_summary(db)
    alerts = AggregationService.get_cluster_alerts(db)

    alert_dtos = [
        {
            "id": a.id,
            "alert_title": a.alert_title,
            "district_name": a.district_name,
            "block_name": a.block_name,
            "village_name": a.village_name,
            "symptom_group": a.symptom_group,
            "case_count": a.case_count,
            "time_window_hours": a.time_window_hours,
            "risk_level": a.risk_level.value,
            "status": a.status,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]

    return StandardResponse(
        data={
            "summary": summary,
            "alerts": alert_dtos
        }
    )

@router.get("/cluster-alerts", response_model=StandardResponse)
def get_cluster_alerts(db: Session = Depends(get_db)):
    alerts = AggregationService.get_cluster_alerts(db)
    items = [
        {
            "id": a.id,
            "alert_title": a.alert_title,
            "district_name": a.district_name,
            "block_name": a.block_name,
            "village_name": a.village_name,
            "symptom_group": a.symptom_group,
            "case_count": a.case_count,
            "time_window_hours": a.time_window_hours,
            "risk_level": a.risk_level.value,
            "status": a.status,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]
    return StandardResponse(data=items)

@router.get("/referral-analytics", response_model=StandardResponse)
def get_referral_analytics(db: Session = Depends(get_db)):
    data = AggregationService.get_referral_trends(db)
    return StandardResponse(data=data)

@router.get("/scheme-analytics", response_model=StandardResponse)
def get_scheme_analytics(db: Session = Depends(get_db)):
    data = AggregationService.get_scheme_analytics(db)
    return StandardResponse(data=data)

@router.get("/system-health", response_model=StandardResponse)
def get_system_health():
    return StandardResponse(
        data=SystemHealthResponse(
            status="HEALTHY",
            database_connected=True,
            integration_mode=settings.INTEGRATION_MODE,
            services={
                "BHASHINI": settings.BHASHINI_MODE,
                "Lyzr_Agents": settings.LYZR_MODE,
                "Milvus_Clinical_RAG": settings.MILVUS_MODE,
                "Neo4j_Scheme_Graph": settings.NEO4J_MODE,
                "Tavily_Search": settings.TAVILY_MODE,
                "n8n_Automation": settings.N8N_MODE,
                "ABDM_Sandbox": settings.ABDM_MODE
            }
        ).model_dump()
    )
