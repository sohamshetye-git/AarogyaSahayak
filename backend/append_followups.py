import os

append_code = """
class CreateFollowUpRequest(BaseModel):
    citizen_id: str
    case_id: Optional[str] = None
    referral_id: Optional[str] = None
    task_type: str
    instructions: str
    priority: str
    due_at: datetime
    contact_mode: Optional[str] = "IN_PERSON"
    source: str = "ASHA_SCHEDULED"

@router.get("/followups/{followup_id}", response_model=StandardResponse)
def get_individual_followup(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="FollowUp not found")
        
    return StandardResponse(data={
        "id": f.id,
        "case_id": f.case_id,
        "case_reference": f.case.reference if f.case else "CASE-2026",
        "citizen_name": f.citizen.display_name if f.citizen else "Citizen",
        "citizen_phone": f.citizen.phone if f.citizen else None,
        "village_name": f.citizen.village_name if f.citizen else "Kalyanpur",
        "task_type": f.task_type,
        "instructions": f.instructions,
        "priority": f.priority.value if hasattr(f.priority, "value") else str(f.priority),
        "due_at": f.due_at.isoformat(),
        "status": f.status,
        "source": f.source,
        "created_by_role": f.created_by_role if hasattr(f, "created_by_role") else "DOCTOR",
        "completed_at": f.completed_at.isoformat() if f.completed_at else None,
        "result": f.result,
        "previous_vitals": [
            {
                "systolic_bp": v.systolic_bp,
                "diastolic_bp": v.diastolic_bp,
                "spo2": v.spo2,
                "pulse": v.pulse,
                "recorded_at": v.recorded_at.isoformat()
            } for v in (f.case.vitals if f.case else [])
        ]
    })

@router.post("/followups", response_model=StandardResponse)
def create_followup(
    req: CreateFollowUpRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, "/asha/followups", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = FollowUp(
        citizen_id=req.citizen_id,
        case_id=req.case_id,
        referral_id=req.referral_id,
        task_type=req.task_type,
        instructions=req.instructions,
        priority=CasePriorityEnum(req.priority),
        due_at=req.due_at,
        source=req.source,
        status="PENDING",
        assigned_user_id=current_user.id
    )
    db.add(f)
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_CREATED",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS"
    )
    db.add(audit)
    db.commit()
    db.refresh(f)
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", "/asha/followups", "FOLLOWUP_CREATED", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

@router.post("/followups/{followup_id}/start", response_model=StandardResponse)
def start_followup(
    followup_id: str,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/start", {})
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="FollowUp not found")
        
    old_status = f.status
    if f.status == "PENDING":
        f.status = "IN_PROGRESS"
    
    if old_status != "IN_PROGRESS":
        audit = AuditLog(
            actor_user_id=current_user.id,
            actor_role="ASHA_WORKER",
            action="FOLLOWUP_STARTED",
            resource_type="FollowUp",
            resource_id=f.id,
            outcome="SUCCESS"
        )
        db.add(audit)
        
    db.commit()
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/start", "FOLLOWUP_STARTED", {}, 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

class ContactResultRequest(BaseModel):
    reason: str
    next_attempt_date: datetime

@router.post("/followups/{followup_id}/contact-result", response_model=StandardResponse)
def followup_contact_result(
    followup_id: str,
    req: ContactResultRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/contact-result", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="FollowUp not found")
        
    f.due_at = req.next_attempt_date
    f.result = f"Unable to reach: {req.reason}"
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_UNREACHABLE",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS",
        metadata_json=req.model_dump()
    )
    db.add(audit)
    db.commit()
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/contact-result", "FOLLOWUP_UNREACHABLE", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

class RescheduleRequest(BaseModel):
    new_due_date: datetime
    reason: str

@router.post("/followups/{followup_id}/reschedule", response_model=StandardResponse)
def reschedule_followup(
    followup_id: str,
    req: RescheduleRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/reschedule", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="FollowUp not found")
        
    f.due_at = req.new_due_date
    f.status = "PENDING"
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_RESCHEDULED",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS",
        metadata_json=req.model_dump()
    )
    db.add(audit)
    db.commit()
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/reschedule", "FOLLOWUP_RESCHEDULED", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

class EscalateRequest(BaseModel):
    reason: str
    urgency: str
    notes: str

@router.post("/followups/{followup_id}/escalate", response_model=StandardResponse)
def escalate_followup(
    followup_id: str,
    req: EscalateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/escalate", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="FollowUp not found")
        
    f.status = "ESCALATED"
    f.result = f"Escalated: {req.reason}"
    f.completed_at = datetime.now(timezone.utc)
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_ESCALATED",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS",
        metadata_json=req.model_dump()
    )
    db.add(audit)
    db.commit()
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/escalate", "FOLLOWUP_ESCALATED", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)
"""

asha_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "app", "routers", "asha.py"))
with open(asha_file_path, "a") as f:
    f.write("\n" + append_code + "\n")
print(f"Appended FollowUp endpoints to {asha_file_path}")
