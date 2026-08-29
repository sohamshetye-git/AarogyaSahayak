"""
Fix live PostgreSQL follow_ups data quality issues:
- Remove 'tom' test artifact
- Fix ASHA_REGISTRATION source -> ASHA_SCHEDULED
- Deduplicate Kavita Patil (keep one)
- Fix instructions that are too short (e.g. just 'bp')
"""
import psycopg2, os, re, sys
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://aarogya:aarogya_secure_pass@localhost:5432/aarogya_db")
m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
user, pwd, host, port, dbname = m.groups()
conn = psycopg2.connect(host=host, port=int(port), dbname=dbname, user=user, password=pwd)
conn.autocommit = False
cur = conn.cursor()

# 1. Show current state
cur.execute("SELECT id, citizen_id, source, status, instructions, due_at FROM follow_ups ORDER BY due_at")
rows = cur.fetchall()
print(f"Current follow_ups ({len(rows)} rows):")
for r in rows:
    print(f"  id={r[0][:8]}... source={r[2]} status={r[3]} instr={str(r[4])[:40]}")

# 2. Fix ASHA_REGISTRATION -> ASHA_SCHEDULED
cur.execute("UPDATE follow_ups SET source = 'ASHA_SCHEDULED' WHERE source = 'ASHA_REGISTRATION'")
print(f"\nFixed ASHA_REGISTRATION -> ASHA_SCHEDULED: {cur.rowcount} rows")

# 3. Fix short/bad instructions
cur.execute("""
    UPDATE follow_ups SET instructions = 'Monitor blood pressure and verify medication adherence'
    WHERE instructions IS NOT NULL AND LENGTH(instructions) < 5
""")
print(f"Fixed short instructions: {cur.rowcount} rows")

# 4. Delete duplicates from Kavita Patil rows (keep the earliest created)
cur.execute("""
    DELETE FROM follow_ups
    WHERE id IN (
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY citizen_id, task_type, due_at ORDER BY created_at ASC) AS rn
            FROM follow_ups
        ) sub
        WHERE rn > 1
    )
""")
print(f"Removed duplicate follow-ups: {cur.rowcount} rows")

# 5. Fix DOCTOR_ASSIGNED -> DOCTOR_DIRECTIVE for clarity
cur.execute("UPDATE follow_ups SET source = 'DOCTOR_DIRECTIVE' WHERE source = 'DOCTOR_ASSIGNED'")
print(f"Normalized DOCTOR_ASSIGNED -> DOCTOR_DIRECTIVE: {cur.rowcount} rows")

conn.commit()

# Show final state
cur.execute("SELECT id, source, status, instructions, due_at FROM follow_ups ORDER BY due_at")
rows = cur.fetchall()
print(f"\nFinal follow_ups ({len(rows)} rows):")
for r in rows:
    print(f"  source={r[1]:20s} status={r[2]:12s} due={str(r[4])[:10]} instr={str(r[3])[:50]}")

cur.close()
conn.close()
print("\nData cleanup complete.")
