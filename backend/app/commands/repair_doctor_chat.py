"""
Doctor Chat Diagnostic & Reconciliation Command
Usage: python -m app.commands.repair_doctor_chat [--dry-run]
"""
import sys
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from app.database import SessionLocal
from app.models import (
    ServiceRequest, DoctorChatThread, DoctorChatMessage,
    TeleconsultationRequest, TeleconsultationMessage, CitizenProfile
)

logger = logging.getLogger("repair-doctor-chat")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def repair_doctor_chat_data(dry_run: bool = False) -> Dict[str, Any]:
    from app.database import engine, Base
    from sqlalchemy import inspect, text
    
    # Ensure all tables exist and all columns are present
    Base.metadata.create_all(bind=engine)
    try:
        inspector = inspect(engine)
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in existing_columns:
                        try:
                            col_type = col.type.compile(engine.dialect)
                            stmt = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
                            with engine.begin() as conn:
                                conn.execute(text(stmt))
                            logger.info(f"Auto-migrated column: {table_name}.{col.name}")
                        except Exception as col_err:
                            logger.warning(f"Could not auto-migrate column {table_name}.{col.name}: {col_err}")
    except Exception as mig_err:
        logger.warning(f"Schema auto-migration notice: {mig_err}")

    db = SessionLocal()
    stats = {
        "total_doctor_service_requests": 0,
        "threads_created": 0,
        "threads_already_existing": 0,
        "tele_requests_linked": 0,
        "messages_reconciled": 0,
        "orphans_found": 0,
        "errors": []
    }

    try:
        # 1. Reconcile ServiceRequests of type DOCTOR_CONSULTATION
        srv_reqs = db.query(ServiceRequest).filter(
            ServiceRequest.request_type.in_(["DOCTOR_CONSULTATION", "TELECONSULTATION"])
        ).all()
        stats["total_doctor_service_requests"] = len(srv_reqs)

        for req in srv_reqs:
            try:
                # Find or link TeleconsultationRequest
                tele_req = db.query(TeleconsultationRequest).filter(
                    (TeleconsultationRequest.service_request_id == req.id) |
                    (TeleconsultationRequest.public_reference == req.request_reference)
                ).first()

                # Check if DoctorChatThread exists
                thread = db.query(DoctorChatThread).filter(
                    (DoctorChatThread.service_request_id == req.id) |
                    ((DoctorChatThread.id == tele_req.id) if tele_req else False)
                ).first()

                if not thread:
                    thread_id = tele_req.id if tele_req else str(uuid.uuid4())
                    # Ensure no PK collision
                    existing_id = db.query(DoctorChatThread).filter(DoctorChatThread.id == thread_id).first()
                    if existing_id:
                        thread = existing_id
                        thread.service_request_id = req.id
                    else:
                        thread = DoctorChatThread(
                            id=thread_id,
                            service_request_id=req.id,
                            citizen_id=req.citizen_id,
                            doctor_id=req.assigned_user_id,
                            facility_id=req.assigned_facility_id or "PHC-09",
                            channel="DOCTOR_CHAT",
                            status=req.status or "WAITING_FOR_DOCTOR"
                        )
                        if not dry_run:
                            db.add(thread)
                            db.flush()
                        stats["threads_created"] += 1
                else:
                    stats["threads_already_existing"] += 1

                if tele_req and not tele_req.service_request_id:
                    tele_req.service_request_id = req.id
                    if not dry_run:
                        db.add(tele_req)
                    stats["tele_requests_linked"] += 1

                # Reconcile TeleconsultationMessages into canonical DoctorChatMessage
                if thread and tele_req:
                    legacy_msgs = db.query(TeleconsultationMessage).filter(
                        TeleconsultationMessage.request_id == tele_req.id
                    ).all()

                    for lm in legacy_msgs:
                        c_id = getattr(lm, "client_message_id", None) or lm.id
                        canon_existing = db.query(DoctorChatMessage).filter(
                            (DoctorChatMessage.client_message_id == c_id) |
                            (DoctorChatMessage.id == lm.id)
                        ).first()

                        if not canon_existing:
                            sender_role = "PHC_DOCTOR" if lm.sender_type == "DOCTOR" else "CITIZEN"
                            c_msg = DoctorChatMessage(
                                id=lm.id,
                                conversation_id=thread.id,
                                service_request_id=req.id,
                                sender_role=sender_role,
                                sender_user_id=lm.sender_id if sender_role == "PHC_DOCTOR" else None,
                                sender_id=lm.sender_id,
                                sender_name=lm.sender_name,
                                body=lm.message_text or "",
                                client_message_id=c_id,
                                status="DELIVERED",
                                created_at=lm.created_at,
                                delivered_at=lm.created_at
                            )
                            if not dry_run:
                                db.add(c_msg)
                            stats["messages_reconciled"] += 1

            except Exception as item_err:
                logger.error(f"Error repairing request {req.id}: {item_err}")
                stats["errors"].append(f"Request {req.id}: {str(item_err)}")

        if not dry_run:
            db.commit()
            logger.info("Database committed successfully.")
        else:
            db.rollback()
            logger.info("DRY RUN completed. No changes written to database.")

    finally:
        db.close()

    return stats


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    print(f"Running Doctor Chat Data Repair (dry_run={is_dry})...")
    res = repair_doctor_chat_data(dry_run=is_dry)
    print("Reconciliation Results:")
    for k, v in res.items():
        print(f"  {k}: {v}")
