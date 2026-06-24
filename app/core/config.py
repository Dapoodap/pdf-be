# pyrefly: ignore [missing-import]
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

UNSAFE_DEFAULTS = {
    "default_unsafe_key_change_me_in_env",
    "default_secret_key_change_me_in_production",
}

class Settings(BaseSettings):
    API_KEY: str = "default_unsafe_key_change_me_in_env"
    DATABASE_URL: str
    GCS_PROJECT_ID: str
    GCS_CLIENT_EMAIL: str
    GCS_BUCKET_NAME: str
    GCS_PRIVATE_KEY: str
    SECRET_KEY: str = "default_secret_key_change_me_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    MIDTRANS_SERVER_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    # Comma-separated list of allowed CORS origins. Set to "*" only in development.
    ALLOWED_ORIGINS: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def validate_production_secrets(self) -> None:
        """
        Call this at startup. Raises RuntimeError if dangerous default values
        are detected in a production-like environment.
        """
        env = os.environ.get("APP_ENV", "development").lower()
        if env in {"production", "staging"}:
            if self.SECRET_KEY in UNSAFE_DEFAULTS:
                raise RuntimeError(
                    "SECRET_KEY is set to an unsafe default value. "
                    "Set a strong random SECRET_KEY in your environment before deploying."
                )
            if self.API_KEY in UNSAFE_DEFAULTS:
                raise RuntimeError(
                    "API_KEY is set to an unsafe default value. "
                    "Set a strong random API_KEY in your environment before deploying."
                )

settings = Settings()
# Uncomment the line below when deploying to staging/production:
# settings.validate_production_secrets()
