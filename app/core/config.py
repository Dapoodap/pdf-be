# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_KEY: str = "default_unsafe_key_change_me_in_env"
    DATABASE_URL: str
    GCS_PROJECT_ID: str
    GCS_CLIENT_EMAIL: str
    GCS_BUCKET_NAME: str
    GCS_PRIVATE_KEY: str
    SECRET_KEY: str = "default_secret_key_change_me_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080 # 7 days

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
