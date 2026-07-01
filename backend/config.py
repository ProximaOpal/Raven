"""
NEXUS CCTV — Application Configuration
Pydantic settings loaded from environment / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Demo / Mock ─────────────────────────────────────────────
    demo_mode: bool = True

    # ── Qwen / DashScope ────────────────────────────────────────
    dashscope_api_key: str = "demo-key"
    qwen_vl_model: str = "qwen-vl-max"
    qwen_vl_fallback_model: str = "qwen-vl-plus"
    qwen_plus_model: str = "qwen-plus"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./nexus.db"

    # ── Security / JWT ───────────────────────────────────────────
    secret_key: str = "nexus-dev-secret-change-in-prod"
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    # ── Twilio ───────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    alert_to_number: str = ""

    # ── SendGrid ─────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    alert_from_email: str = "nexus@example.com"
    alert_to_email: str = "soc@example.com"

    # ── Alibaba Cloud OSS ────────────────────────────────────────
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = "nexus-cctv-evidence"
    oss_endpoint: str = "https://oss-ap-southeast-1.aliyuncs.com"

    # ── Redis / Celery ───────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── App ──────────────────────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    # ── Evidence Storage ─────────────────────────────────────────
    evidence_store_path: str = "./evidence_store"

    @property
    def is_twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and not self.demo_mode)

    @property
    def is_sendgrid_configured(self) -> bool:
        return bool(self.sendgrid_api_key and not self.demo_mode)

    @property
    def is_oss_configured(self) -> bool:
        return bool(self.oss_access_key_id and self.oss_access_key_secret and not self.demo_mode)

    @property
    def is_qwen_configured(self) -> bool:
        return bool(self.dashscope_api_key and self.dashscope_api_key != "demo-key" and not self.demo_mode)


@lru_cache
def get_settings() -> Settings:
    return Settings()
