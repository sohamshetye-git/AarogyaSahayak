import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path to resolve 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "app")))
from app.config import settings
from app.models import AuditLog

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_duplicates():
    db = SessionLocal()
    try:
        # We need to find duplicate CASE_ACKNOWLEDGED and REFERRAL_ACKNOWLEDGED events for the same resource
        # Since sqlite doesn't support complex window functions in delete, we'll fetch and delete programmatically.
        
        for action_type in ["CASE_ACKNOWLEDGED", "REFERRAL_ACKNOWLEDGED"]:
            logs = db.query(AuditLog).filter(AuditLog.action == action_type).order_by(AuditLog.created_at.asc()).all()
            
            # Keep track of first occurrences
            seen_resources = set()
            duplicates_to_delete = []
            
            for log in logs:
                if log.resource_id in seen_resources:
                    duplicates_to_delete.append(log)
                else:
                    seen_resources.add(log.resource_id)
            
            if duplicates_to_delete:
                print(f"Found {len(duplicates_to_delete)} duplicate {action_type} logs. Deleting...")
                for d in duplicates_to_delete:
                    db.delete(d)
                
                db.commit()
                print(f"Deleted duplicates for {action_type}.")
            else:
                print(f"No duplicates found for {action_type}.")
                
    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_duplicates()
