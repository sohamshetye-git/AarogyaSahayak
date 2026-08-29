import psycopg2, os, sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aarogya_db")
import re
m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
if not m:
    print(f"Cannot parse DATABASE_URL: {db_url}")
    sys.exit(1)
user, pwd, host, port, dbname = m.groups()

try:
    conn = psycopg2.connect(host=host, port=int(port), dbname=dbname, user=user, password=pwd)
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

cur = conn.cursor()

# Get follow_ups columns from Postgres
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'follow_ups'
    ORDER BY ordinal_position
""")
db_cols = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

print(f"\n=== POSTGRES follow_ups table ({len(db_cols)} columns) ===")
for name, (dtype, nullable) in db_cols.items():
    print(f"  {name:45s} {dtype:20s} nullable={nullable}")

# SQLAlchemy model columns
model_cols = [
    "id", "case_id", "citizen_id", "referral_id", "consultation_id",
    "created_by_id", "created_by_role", "source", "task_type", "reason",
    "assigned_role", "assigned_user_id", "instructions",
    "measurements_to_repeat", "adherence_required", "escalation_conditions",
    "priority", "due_at", "status", "started_at", "completed_at",
    "completion_notes", "symptoms_outcome", "result", "sync_status",
    "created_at", "updated_at"
]

print(f"\n=== SQLAlchemy FollowUp model ({len(model_cols)} columns) ===")
for c in model_cols:
    in_db = c in db_cols
    flag = "OK" if in_db else "MISSING IN DB"
    print(f"  {c:45s} {flag}")

missing = [c for c in model_cols if c not in db_cols]
extra = [c for c in db_cols if c not in model_cols]

print(f"\n=== DIFF SUMMARY ===")
print(f"  Missing in DB (need migration): {missing}")
print(f"  Extra in DB (not in model):     {extra}")

cur.close()
conn.close()
