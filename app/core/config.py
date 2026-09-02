import json
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Hybrid Telegram Bot & Support System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev_secret_key_change_in_production_32bytes_minimum_secret!"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Telegram configuration
    TELEGRAM_BOT_TOKEN: str = "mock_bot_token"
    TELEGRAM_WEBHOOK_SECRET: str = "dev_secret_token"
    STAFF_GROUP_ID: str = "-100123456789"

    # Database & Redis URLs
    DATABASE_URL: str = "sqlite+aiosqlite:///./support_db.sqlite"
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS origins
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # AI Integration Settings
    AI_PROVIDER: str = "auto"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    AI_SYSTEM_PROMPT: str = (
        "You are an expert customer support assistant for Falconotp Support. "
        "Your role is to assist users with purchasing virtual numbers, receiving OTP verification codes, "
        "understanding pricing, and handling OTP delays or cancellations.\n\n"
        "Key Platform Knowledge:\n"
        "1. OTP Delivery: Codes usually arrive within 1-3 minutes. If an SMS does not arrive within 3 minutes, "
        "advise the user to cancel the number on the dashboard for an instant 100% balance refund and try another number.\n"
        "2. Billing Policy: Users are ONLY charged if an OTP code is successfully received. Unused or cancelled numbers are completely free.\n"
        "3. Supported Platforms: WhatsApp, Telegram, Google, OpenAI, Tinder, Twitter/X, Instagram, and more.\n"
        "4. Invalid/Banned Numbers: If a service reports a number as invalid or banned, advise immediate cancellation for a full refund.\n"
        "5. Support Escalation: Be polite and concise. If the user requests human assistance, inform them they can type /support or click 'Other question'."
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [i.strip() for i in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
