from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 10080  # 7 days

    # AI
    gemini_api_key: str

    # External APIs
    news_api_key: str = ""
    fred_api_key: str = ""
    alpha_vantage_key: str = ""
    twelvedata_api_key: str = ""
    finnhub_api_key: str = ""
    groww_api_key: str = ""
    
    # Database
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # Redis
    redis_url: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()