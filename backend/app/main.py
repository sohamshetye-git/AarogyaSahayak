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
from app.routers import auth, citizen, asha, doctor, admin, reports, websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aarogya-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Aarogya Sahayak Backend...")
    # Initialize DB tables via Alembic (create_all removed for production)
    seed_database()
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

# Validation Error Handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    field_errors = {}
    for error in exc.errors():
        field_name = ".".join([str(loc) for loc in error["loc"] if loc not in ("body", "query", "path")])
        field_errors[field_name or "request"] = error["msg"]
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Please check the entered information.",
                "fields": field_errors
            },
            "request_id": request_id
        }
    )

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(citizen.router, prefix=settings.API_V1_STR)
app.include_router(asha.router, prefix=settings.API_V1_STR)
app.include_router(doctor.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
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
