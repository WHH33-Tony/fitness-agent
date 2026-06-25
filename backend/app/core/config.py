from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fitness Coach System"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    users_database_url: str = "mysql+pymysql://root:root123456@localhost:3306/users?charset=utf8mb4"
    sports_database_url: str = "mysql+pymysql://root:root123456@localhost:3306/sports?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"
    mcp_server_url: str = "http://localhost:9001"
    dashscope_api_key: str = ""
    xfyun_app_id: str = ""
    xfyun_api_key: str = ""
    xfyun_api_secret: str = ""
    qwen_model: str = "qwen-plus"
    upload_dir: str = "uploads"
    public_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
