from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    app_log_level: str = "INFO"
    app_cors_origins: str = "http://localhost:3000"
    app_checkpointer: Literal["memory", "postgres"] = "memory"

    database_url: str = "postgresql+asyncpg://vyapaar:change-me@localhost:5432/vyapaar"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    redis_url: str = "redis://localhost:6379/0"
    redis_required: bool = False

    auth_jwt_secret: SecretStr = SecretStr("development-only-change-me-32-bytes")
    auth_approval_secret: SecretStr = SecretStr("development-approval-secret-change-me")
    auth_jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    auth_access_token_minutes: int = Field(default=30, ge=1)
    auth_refresh_token_days: int = Field(default=30, ge=1, le=365)
    auth_approval_token_minutes: int = Field(default=10, ge=1, le=60)
    auth_otp_secret: SecretStr = SecretStr("development-otp-secret-change-me-32")
    auth_otp_expiry_minutes: int = Field(default=5, ge=1, le=15)
    auth_otp_resend_seconds: int = Field(default=45, ge=15, le=300)
    auth_otp_max_attempts: int = Field(default=5, ge=3, le=10)
    auth_otp_max_resends: int = Field(default=3, ge=1, le=10)
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_oauth_redirect_uri: str | None = (
        "http://localhost:8000/api/v1/auth/oauth/google/callback"
    )
    apple_oauth_client_id: str | None = None

    llm_provider: Literal["disabled", "azure", "azure_foundry", "enabled"] = "disabled"
    llm_model: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: SecretStr | None = None
    azure_openai_api_version: str | None = None

    sarvam_api_key: SecretStr | None = None
    sarvam_stt_model: str = "saaras:v4"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "ritu"
    sarvam_tts_pace: float = Field(default=1.0, ge=0.5, le=2.0)
    sarvam_tts_temperature: float = Field(default=0.6, ge=0.01, le=2.0)
    sarvam_tts_sample_rate: int = Field(default=24000)
    sarvam_tts_codec: str = "mp3"
    sarvam_tts_bitrate: str = "192k"

    # Meta WhatsApp Cloud API (Coming Soon)
    whatsapp_access_token: SecretStr | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_verify_token: SecretStr | None = None
    whatsapp_app_secret: SecretStr | None = None
    whatsapp_graph_api_version: str | None = None

    # Telegram Bot Channel
    telegram_bot_token: SecretStr | None = None
    telegram_webhook_secret: SecretStr | None = None
    telegram_bot_username: str = "PaytmOneVyapar_bot"

    resend_api_key: SecretStr | None = None
    resend_from_email: str = "Paytm ONE Vyapar <auth@tuboxlabs.com>"

    telemetry_enabled: bool = False
    telemetry_otlp_endpoint: str | None = None
    sentry_dsn: SecretStr | None = None

    a2a_agent_id: UUID = UUID("11111111-1111-4111-8111-111111111111")
    a2a_signing_secret: SecretStr = SecretStr("development-a2a-secret-change-me")
    a2a_max_clock_skew_seconds: int = Field(default=300, ge=30, le=3600)

    forecast_model: Literal["baseline", "lightgbm"] = "baseline"
    forecast_model_path: str = "models/demand.txt"
    forecast_min_training_rows: int = Field(default=60, ge=20)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @field_validator("sarvam_api_key", mode="before")
    @classmethod
    def normalize_sarvam_key(cls, value):
        if isinstance(value, str):
            normalized = value.strip().strip('"').strip("'").strip()
            return normalized or None
        return value

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.app_env != "production":
            return self
        jwt_secret = self.auth_jwt_secret.get_secret_value()
        approval_secret = self.auth_approval_secret.get_secret_value()
        a2a_secret = self.a2a_signing_secret.get_secret_value()
        otp_secret = self.auth_otp_secret.get_secret_value()
        if len(jwt_secret) < 32 or jwt_secret.startswith("development-"):
            raise ValueError("AUTH_JWT_SECRET must contain at least 32 characters in production")
        if len(approval_secret) < 32 or approval_secret.startswith("development-"):
            raise ValueError(
                "AUTH_APPROVAL_SECRET must contain at least 32 characters in production"
            )
        if len(a2a_secret) < 32 or a2a_secret.startswith("development-"):
            raise ValueError("A2A_SIGNING_SECRET must contain at least 32 characters in production")
        if len(otp_secret) < 32 or otp_secret.startswith("development-"):
            raise ValueError("AUTH_OTP_SECRET must contain at least 32 characters in production")
        if not self.database_url.startswith("postgresql+"):
            raise ValueError("DATABASE_URL must use an async PostgreSQL driver in production")
        if self.app_checkpointer != "postgres":
            raise ValueError("APP_CHECKPOINTER must be postgres in production")
        if self.llm_provider != "disabled":
            if not all([self.azure_openai_endpoint, self.azure_openai_api_key, self.llm_model]):
                raise ValueError(
                    "Azure LLM provider is selected but its credentials are incomplete"
                )
            is_v1_endpoint = self.azure_openai_endpoint.rstrip("/").endswith("/openai/v1")
            if not is_v1_endpoint and not self.azure_openai_api_version:
                raise ValueError("AZURE_OPENAI_API_VERSION is required for a deployment endpoint")
            if "change-me" in self.azure_openai_api_key.get_secret_value().lower():
                raise ValueError("AZURE_OPENAI_API_KEY cannot be a placeholder in production")
        whatsapp_values = [
            self.whatsapp_access_token,
            self.whatsapp_phone_number_id,
            self.whatsapp_verify_token,
            self.whatsapp_app_secret,
            self.whatsapp_graph_api_version,
        ]
        if any(whatsapp_values) and not all(whatsapp_values):
            raise ValueError("WhatsApp is partially configured")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
