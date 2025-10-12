from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "PT Teknologi Aeronautika Utama"
    SECRET_KEY: str = "R4h4514-S3k4li"
    DATABASE_URL: str = "mysql+pymysql://user:pass@localhost:3306/ptaero"
    DEFAULT_LANG: str = "id"
    BASE_URL: str = "http://localhost:8000"
    MAIL_HOST: str = ""
    MAIL_PORT: int = 587
    MAIL_USER: str = ""
    MAIL_PASS: str = ""
    MAIL_FROM: str = "noreply@example.com"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
