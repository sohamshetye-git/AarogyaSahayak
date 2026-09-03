from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uuid
import logging

from app.config import settings
from app.database import engine, Base
from app.seeds.seed_data import seed_database
from app.routers import auth, citizen, teleconsultation, asha, doctor, admin, reports, websocket, ai, schemes, doctor_prescriptions, doctor_alerts

# ... (middleware) ...


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aarogya-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Aarogya Sahayak Backend...")
    # Create tables if not existing
    import app.models
    import app.models.facilities
    import app.models.schemes
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate missing columns for SQLite development DB
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in existing_columns:
                        try:
                            col_type = col.type.compile(engine.dialect)
                            default_clause = ""
                            if col.default is not None and hasattr(col.default, "arg"):
                                val = col.default.arg
                                if isinstance(val, (int, float, bool)):
                                    default_clause = f" DEFAULT {int(val) if isinstance(val, bool) else val}"
                            stmt = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default_clause}"
                            with engine.begin() as conn:
                                conn.execute(text(stmt))
                            logger.info(f"Auto-migrated column: {table_name}.{col.name}")
                        except Exception as col_err:
                            logger.warning(f"Could not auto-migrate column {table_name}.{col.name}: {col_err}")
    except Exception as mig_err:
        logger.warning(f"Schema auto-migration notice: {mig_err}")
    
    # Seed database if empty
    seed_database()

    # Explicitly ensure Government Schemes Knowledge Base is populated
    try:
        from app.models import SchemeModel
        from app.schemes.import_kb import import_knowledge_base
        from app.database import SessionLocal
        with SessionLocal() as db_sess:
            count = db_sess.query(SchemeModel).count()
            if count == 0:
                logger.info("Scheme catalog is empty. Importing knowledge base...")
                import_knowledge_base(db_session=db_sess)
                logger.info(f"Imported schemes knowledge base successfully. Total schemes now: {db_sess.query(SchemeModel).count()}")
            else:
                logger.info(f"Scheme catalog already populated with {count} schemes.")
    except Exception as e:
        logger.error(f"Failed to populate schemes knowledge base in lifespan: {e}")
    
    # Ingest clinical guidelines into Milvus RAG
    try:
        import os
        from app.ai.rag.clinical_rag import clinical_rag_service, ingest_manifest
        manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge/clinical/manifest.yaml"))
        if os.path.exists(manifest_path) and clinical_rag_service.count() == 0:
            ingest_manifest(manifest_path)
            logger.info("Clinical guideline RAG index loaded.")
    except Exception as e:
        logger.warning(f"Could not load clinical guidelines: {e}")

    logger.info("Backend initialized with deterministic demo data.")
    yield
    logger.info("Shutting down Aarogya Sahayak Backend.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Voice-First Rural Healthcare Platform Backend",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Request ID and Request Logging Middleware
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Global Error Handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"Unhandled Exception on {request.method} {request.url.path} [request_id={request_id}]: {exc}", exc_info=True)
    origin = request.headers.get("origin", "*")
    error_msg = "An unexpected error occurred while processing your request. Please try again."
    err_detail = str(exc) if settings.ENVIRONMENT in ("staging", "development", "local") else None
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
        content={
            "error": {
                "code": "SERVER_ERROR",
                "message": error_msg,
                "detail": err_detail
            },
            "request_id": request_id
        }
    )


from app.routers import auth, citizen, asha, doctor, doctor_chat, doctor_prescriptions, doctor_alerts, admin, reports, websocket, ai, schemes, locations, voice

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(locations.router, prefix=settings.API_V1_STR)
app.include_router(citizen.router, prefix=settings.API_V1_STR)
app.include_router(voice.router, prefix=settings.API_V1_STR)
app.include_router(teleconsultation.router, prefix=settings.API_V1_STR)
app.include_router(doctor_chat.router, prefix=settings.API_V1_STR)
app.include_router(doctor_chat.canonical_care_conv_router, prefix=settings.API_V1_STR)
app.include_router(doctor_chat.canonical_conv_router, prefix=settings.API_V1_STR)
app.include_router(doctor_chat.canonical_care_req_router, prefix=settings.API_V1_STR)
app.include_router(doctor_chat.canonical_citizen_doc_router, prefix=settings.API_V1_STR)
app.include_router(asha.router, prefix=settings.API_V1_STR)
app.include_router(doctor.router, prefix=settings.API_V1_STR)
app.include_router(doctor_prescriptions.router, prefix=settings.API_V1_STR)
app.include_router(doctor_alerts.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(schemes.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router, prefix=settings.API_V1_STR)
app.include_router(websocket.ws_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "aarogya-sahayak-backend",
        "version": settings.APP_VERSION,
        "integration_mode": settings.INTEGRATION_MODE
    }

@app.get("/")
def root():
    return {
        "platform": "Aarogya Sahayak",
        "tagline": "Voice-First Rural Healthcare Assistance Ecosystem for India",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }

app.include_router(schemes.router, prefix=settings.API_V1_STR)
