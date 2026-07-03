"""
Raven AI CCTV — Application Configuration
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
    # Custom workspace endpoint (optional — falls back to public DashScope)
    dashscope_api_host: str = ""
    dashscope_openai_base_url: str = ""   # OpenAI-compatible /compatible-mode/v1
    dashscope_base_url: str = ""          # Native DashScope /api/v1
    qwen_vl_model: str = "qwen-vl-max"
    qwen_vl_fallback_model: str = "qwen-vl-plus"
    qwen_plus_model: str = "qwen-plus"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./raven.db"

    # ── Security / JWT ───────────────────────────────────────────
    secret_key: str = "raven-dev-secret-change-in-prod"
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    # ── Twilio ───────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    alert_to_number: str = ""

    # ── SendGrid ─────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    alert_from_email: str = "raven@example.com"
    alert_to_email: str = "soc@example.com"

    # ── Alibaba Cloud OSS ────────────────────────────────────────
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = "Raven-evidence"
    oss_endpoint: str = "https://oss-ap-southeast-1.aliyuncs.com"

    # ── Redis / Celery ───────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── App ──────────────────────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    log_level: str = "INFO"

    # ── Security & Integrations ──────────────────────────────────
    openclaw_gateway_token: str = ""
    public_dashboard_url: str = "http://127.0.0.1:8000"
    cors_allowed_origins: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://raven-klqu.onrender.com",
        # Netlify deployments (main site + preview URLs)
        "https://cheerful-klepon-c28908.netlify.app",
        "https://*.netlify.app",
        "https://*.netlify.com",
    ]

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
