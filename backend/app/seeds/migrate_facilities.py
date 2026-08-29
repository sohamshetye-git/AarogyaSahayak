import sqlite3
import os

def migrate_facilities_schema(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check facilities columns
    cur.execute("PRAGMA table_info(facilities)")
    existing_cols = {c[1] for c in cur.fetchall()}

    columns_to_add = [
        ("public_reference", "VARCHAR(50)"),
        ("official_name", "VARCHAR(255)"),
        ("localized_name", "JSON"),
        ("ownership", "VARCHAR(50) DEFAULT 'GOVERNMENT'"),
        ("authority", "VARCHAR(150) DEFAULT 'Public Health Department, Maharashtra'"),
        ("state", "VARCHAR(100) DEFAULT 'Maharashtra'"),
        ("district", "VARCHAR(100) DEFAULT 'District 04'"),
        ("block", "VARCHAR(100) DEFAULT 'Kalyanpur Block'"),
        ("village", "VARCHAR(150)"),
        ("pincode", "VARCHAR(10)"),
        ("landmark", "VARCHAR(255)"),
        ("latitude", "FLOAT DEFAULT 18.5204"),
        ("longitude", "FLOAT DEFAULT 73.8567"),
        ("phone", "VARCHAR(30)"),
        ("email", "VARCHAR(150)"),
        ("emergency_helpline", "VARCHAR(30) DEFAULT '108'"),
        ("verification_status", "VARCHAR(50) DEFAULT 'VERIFIED'"),
        ("source_id", "VARCHAR(100) DEFAULT 'GOVT_REGISTRY_NIN'"),
        ("source_name", "VARCHAR(150) DEFAULT 'National Health Portal'"),
        ("last_verified_at", "DATETIME"),
        ("updated_at", "DATETIME")
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE facilities ADD COLUMN {col_name} {col_type}")
                print(f"Added column {col_name} to facilities table")
            except Exception as e:
                print(f"Could not add column {col_name}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "aarogya.db"))
    print(f"Migrating {db_file}...")
    migrate_facilities_schema(db_file)
    print("Migration completed.")
