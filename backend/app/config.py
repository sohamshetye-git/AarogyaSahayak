from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_NAME: str = "Aarogya Sahayak API"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Server
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    # Database
    DATABASE_URL: str = "sqlite:///./aarogya.db"
    
    # Security
    JWT_SECRET: str = "aarogya_super_secret_jwt_key_development_only_2026"
    JWT_REFRESH_SECRET: str = "aarogya_super_secret_refresh_jwt_key_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours for demo convenience
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Integration Modes (mock vs live)
    INTEGRATION_MODE: str = "mock"
    BHASHINI_MODE: str = "mock"
    SARVAM_MODE: str = "mock"
    LYZR_MODE: str = "mock"
    GEMINI_MODE: str = "mock"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MILVUS_MODE: str = "mock"
    NEO4J_MODE: str = "mock"
    TAVILY_MODE: str = "mock"
    SWYTCHCODE_MODE: str = "mock"
    N8N_MODE: str = "mock"
    ABDM_MODE: str = "mock"
    GOOGLE_MAPS_MODE: str = "auto" # 'live', 'mock', or 'auto' (uses live if key present)
    
    # API Credentials (Optional in mock mode)
    GEMINI_API_KEY: Optional[str] = None
    SARVAM_API_KEY: Optional[str] = None
    LYZR_API_KEY: Optional[str] = None
    BHASHINI_API_KEY: Optional[str] = None
    BHASHINI_USER_ID: Optional[str] = None
    BHASHINI_PIPELINE_ID: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    SWYTCHCODE_API_KEY: Optional[str] = None
    GOOGLE_MAPS_SERVER_KEY: Optional[str] = None
    GOOGLE_PLACES_DAILY_LIMIT: int = 500
    
    # Vector & Graph DB URIs
    MILVUS_URI: str = "http://localhost:19530"
    MILVUS_TOKEN: Optional[str] = None
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "aarogya_password"
    
    # Webhooks & Interoperability
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook"
    N8N_WEBHOOK_SECRET: str = "aarogya_n8n_secret"
    ABDM_BASE_URL: str = "https://dev.abdm.gov.in/gateway/v0.5"
    ABDM_CLIENT_ID: Optional[str] = None
    ABDM_CLIENT_SECRET: Optional[str] = None

    # AI Usage Governance & Guardrails
    AI_DAILY_REQUEST_LIMIT: int = 250
    AI_PER_USER_MINUTE_LIMIT: int = 15
    GEMINI_MAX_INPUT_CHARACTERS: int = 10000
    GEMINI_MAX_OUTPUT_TOKENS: int = 1024
    GEMINI_DAILY_REQUEST_LIMIT: int = 100
    BHASHINI_MAX_AUDIO_SECONDS: float = 60.0
    BHASHINI_MAX_AUDIO_BYTES: int = 10 * 1024 * 1024 # 10MB
    TAVILY_DAILY_REQUEST_LIMIT: int = 50
    TAVILY_CACHE_TTL_SECONDS: int = 86400 # 24 hours
    LYZR_DAILY_REQUEST_LIMIT: int = 100
    PROVIDER_FAILURE_THRESHOLD: int = 5
    PROVIDER_CIRCUIT_OPEN_SECONDS: int = 60

    # Citizen OTP & Guest Access
    OTP_MODE: str = "MOCK" # 'MOCK', 'BHASHINI', 'SARVAM', 'TWILIO', 'MSG91'
    OTP_TEST_CODE: str = "123456"
    OTP_EXPIRY_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    GUEST_SESSION_TTL_HOURS: int = 24
    OTP_SMS_PROVIDER_API_KEY: Optional[str] = None
    OTP_SMS_SENDER_ID: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")

settings = Settings()

def validate_production_settings():
    env = (settings.ENVIRONMENT or "").lower()
    if env in ["production", "prod"] and (settings.OTP_MODE or "").upper() == "MOCK":
        raise RuntimeError("CRITICAL SECURITY ERROR: OTP_MODE=MOCK is strictly forbidden in production environments!")

validate_production_settings()

