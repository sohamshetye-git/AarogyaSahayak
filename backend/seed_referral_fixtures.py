"""
Clean and adapt referral fixture records to existing database cases.
Guarantees case-canonical alignment and prevents cross-patient clinical data leakage.
"""
import psycopg2, os, re
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://aarogya:aarogya_secure_pass@localhost:5432/aarogya_db')
m = re.match(r'postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
user, pwd, host, port, dbname = m.groups()
conn = psycopg2.connect(host=host, port=int(port), dbname=dbname, user=user, password=pwd)
conn.autocommit = False
cur = conn.cursor()

now = datetime.now(timezone.utc)

print("--- SEEDING DOCTOR REFERRAL QUEUE FIXTURES ACROSS EXISTING CASES ---")

# 1. Sunita Devi (case-canonical-001) -> URGENT PENDING_DOCTOR_REVIEW (Preeclampsia risk)
cur.execute("SELECT id FROM cases WHERE id = 'case-canonical-001' OR reference = 'CASE-DEMO-004'")
c_sunita = cur.fetchone()
if c_sunita:
    sunita_case_id = c_sunita[0]
    cur.execute("SELECT id FROM referrals WHERE case_id = %s", (sunita_case_id,))
    r1 = cur.fetchone()
    reason_sunita = "Pregnancy-related warning signs: Elevated BP (150/98 mmHg), severe headache and pedal edema recorded. Urgent medical-officer review recommended."
    if r1:
        cur.execute("""
            UPDATE referrals 
            SET status = 'PENDING_DOCTOR_REVIEW', urgency = 'URGENT',
                reason = %s,
                created_at = %s, acknowledged_at = NULL, acknowledged_by = NULL
            WHERE id = %s
        """, (reason_sunita, now - timedelta(minutes=18), r1[0]))
    else:
        cur.execute("""
            INSERT INTO referrals (id, reference, case_id, to_facility_id, to_facility_name, urgency, reason, status, transport_assistance_required, created_at)
            VALUES ('ref-sunita-001', 'REF-2026-778844', %s, 'FAC-PHC-09', 'Kalyanpur Primary Health Centre', 'URGENT', %s, 'PENDING_DOCTOR_REVIEW', FALSE, %s)
        """, (sunita_case_id, reason_sunita, now - timedelta(minutes=18)))
    cur.execute("UPDATE cases SET status = 'REFERRED_TO_PHC', priority = 'URGENT', safety_rule_triggered = TRUE, safety_rule_reason = %s WHERE id = %s", (reason_sunita, sunita_case_id))

# 2. Meena Bai (case-canonical-002) -> PATIENT_ARRIVED (Hypoxemia)
cur.execute("SELECT id FROM cases WHERE id = 'case-canonical-002' OR reference = 'CASE-DEMO-002'")
c_meena = cur.fetchone()
if c_meena:
    meena_case_id = c_meena[0]
    reason_meena = "Hypoxemia warning signs (SpO2 91%) and acute nocturnal breathlessness recorded."
    cur.execute("SELECT id FROM referrals WHERE case_id = %s", (meena_case_id,))
    r2 = cur.fetchone()
    if not r2:
        cur.execute("""
            INSERT INTO referrals (id, reference, case_id, to_facility_id, to_facility_name, urgency, reason, status, transport_assistance_required, created_at, acknowledged_at, acknowledged_by)
            VALUES ('ref-meena-002', 'REF-2026-882101', %s, 'FAC-PHC-09', 'Kalyanpur Primary Health Centre', 'URGENT', %s, 'PATIENT_ARRIVED', TRUE, %s, %s, 'Dr. Abhinav Sharma')
        """, (meena_case_id, reason_meena, now - timedelta(hours=1, minutes=15), now - timedelta(minutes=45)))
    else:
        cur.execute("""
            UPDATE referrals SET status = 'PATIENT_ARRIVED', urgency = 'URGENT', reason = %s, acknowledged_at = %s WHERE id = %s
        """, (reason_meena, now - timedelta(minutes=45), r2[0]))
    cur.execute("UPDATE cases SET status = 'PATIENT_ARRIVED', priority = 'URGENT', safety_rule_triggered = TRUE, safety_rule_reason = %s WHERE id = %s", (reason_meena, meena_case_id))

conn.commit()
cur.close()
conn.close()
print("[SUCCESS] Referral fixtures updated with case-canonical clinical reasons.")
