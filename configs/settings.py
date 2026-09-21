from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    CURRENT_ENVIRONMENT: str = "development"
    
    # DB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "dauth_service"
    REDIS_URL: str
    
    # Auth & JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_KEY: str
    SECRET_KEY: str
    
    # Email SMTP
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_USER: str
    EMAIL_PASSWORD: str
    
    # Mock Mode Configuration
    MOCK_MODE: bool = False
    MOCK_EMAIL: str = "test@debuggerstechnologies.com"
    MOCK_OTP: str = "123456"
    MOCK_SUBSCRIPTION_STATE: str = "none" # "none" | "ending_soon" | "grace_period" | "expired"
    GRACE_PERIOD_DAYS: int = 7

    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    
    # Frontend/Backend URLs
    REDIRECT_BASEURL: str = "http://127.0.0.1:8000"
    FRONTEND_URL: str = "http://localhost:5173"

    # SMS / MSG91
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_TEMPLATE_ID: Optional[str] = None
    MSG91_WIDGET_ID: Optional[str] = None
    MOC_OTP: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
