"""
CLI Diagnostic Runner for Citizen Identity and Relational Integrity
Usage: python backend/diagnostics.py
"""

import os
import sys
import json

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.diagnostic_service import IdentityDiagnosticService

def main():
    db = SessionLocal()
    try:
        print("\n=======================================================")
        print("   AAROGYA SAHAYAK - CITIZEN IDENTITY INTEGRITY REPORT")
        print("=======================================================\n")
        report = IdentityDiagnosticService.run_full_diagnostic(db)
        print(json.dumps(report, indent=2))
        print("\n=======================================================")
        print(f"Status: {report['summary']['status']} | Total Issues: {report['summary']['total_issues_found']}")
        print("=======================================================\n")
    finally:
        db.close()

if __name__ == "__main__":
    main()
