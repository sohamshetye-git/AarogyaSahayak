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

print("--- CLEANING ARTIFACT DATA ('tom' and numbered duplicates) ---")

# 1. Check if 'tom' citizen exists and remove or rename
cur.execute("SELECT id, display_name FROM citizen_profiles WHERE LOWER(display_name) = 'tom'")
tom_citizens = cur.fetchall()
print(f"Found 'tom' citizen profiles: {tom_citizens}")

for t_id, t_name in tom_citizens:
    # Delete related follow_ups, cases, visits
    cur.execute("DELETE FROM follow_ups WHERE citizen_id = %s", (t_id,))
    cur.execute("DELETE FROM vital_records WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (t_id,))
    cur.execute("DELETE FROM symptom_observations WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (t_id,))
    cur.execute("DELETE FROM asha_visits WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (t_id,))
    cur.execute("DELETE FROM referrals WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (t_id,))
    cur.execute("DELETE FROM cases WHERE citizen_id = %s", (t_id,))
    cur.execute("DELETE FROM citizen_profiles WHERE id = %s", (t_id,))
    print(f"Purged test artifact 'tom' (id: {t_id})")

# 2. Check duplicate numbered citizens e.g. "Kavita Patil 707269"
cur.execute("SELECT id, display_name FROM citizen_profiles WHERE display_name ~ 'Kavita Patil [0-9]+'")
numbered_kavitas = cur.fetchall()
print(f"Found numbered duplicate Kavitas: {len(numbered_kavitas)}")

# Keep at most one canonical Kavita Patil
cur.execute("SELECT id, display_name FROM citizen_profiles WHERE display_name = 'Kavita Patil'")
canonical_kavita = cur.fetchone()

if not canonical_kavita and numbered_kavitas:
    # Rename the first one to canonical "Kavita Patil"
    first_id, first_name = numbered_kavitas[0]
    cur.execute("UPDATE citizen_profiles SET display_name = 'Kavita Patil' WHERE id = %s", (first_id,))
    print(f"Promoted {first_name} ({first_id}) to 'Kavita Patil'")
    remaining = numbered_kavitas[1:]
else:
    remaining = numbered_kavitas

for rem_id, rem_name in remaining:
    cur.execute("DELETE FROM follow_ups WHERE citizen_id = %s", (rem_id,))
    cur.execute("DELETE FROM vital_records WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (rem_id,))
    cur.execute("DELETE FROM symptom_observations WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (rem_id,))
    cur.execute("DELETE FROM asha_visits WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (rem_id,))
    cur.execute("DELETE FROM referrals WHERE case_id IN (SELECT id FROM cases WHERE citizen_id = %s)", (rem_id,))
    cur.execute("DELETE FROM cases WHERE citizen_id = %s", (rem_id,))
    cur.execute("DELETE FROM citizen_profiles WHERE id = %s", (rem_id,))
    print(f"Purged duplicate numbered citizen {rem_name} ({rem_id})")

conn.commit()

# Print remaining follow_ups
cur.execute("""
    SELECT f.id, c.display_name, f.source, f.status, f.due_at, f.instructions
    FROM follow_ups f
    LEFT JOIN citizen_profiles c ON f.citizen_id = c.id
    ORDER BY f.due_at
""")
rows = cur.fetchall()
print(f"\nRemaining Clean Follow-ups ({len(rows)} rows):")
for r in rows:
    print(f"  Citizen: {str(r[1]):25s} | Source: {str(r[2]):18s} | Status: {str(r[3]):10s} | Due: {str(r[4])[:10]} | Notes: {str(r[5])[:45]}")

cur.close()
conn.close()
print("\nDatabase clean-up finished successfully.")
