from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Configure SQLite or PostgreSQL engine
import os

app_env = os.environ.get("APP_ENV", "development")
db_url = settings.DATABASE_URL

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Safety mechanism: ensure we don't drop/delete prod data in tests
if app_env == "test":
    if db_url.startswith("sqlite"):
        db_url = f"sqlite:///{os.path.join(backend_dir, 'aarogya_test.db').replace('\\', '/')}"
    elif db_url.startswith("postgresql"):
        if not db_url.endswith("_test"):
            db_url = db_url + "_test"
elif db_url.startswith("sqlite:///."):
    # Convert relative sqlite path to absolute backend dir path
    rel_path = db_url[len("sqlite:///."):]
    db_url = f"sqlite:///{os.path.join(backend_dir, rel_path.lstrip('/\\')).replace('\\', '/')}"

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
