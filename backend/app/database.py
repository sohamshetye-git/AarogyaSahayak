from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Configure SQLite or PostgreSQL engine
import os

app_env = os.environ.get("APP_ENV", "development")
db_url = settings.DATABASE_URL

# Safety mechanism: ensure we don't drop/delete prod data in tests
if app_env == "test":
    if db_url.startswith("sqlite"):
        db_url = "sqlite:///./aarogya_test.db"
    elif db_url.startswith("postgresql"):
        if not db_url.endswith("_test"):
            db_url = db_url + "_test"

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
