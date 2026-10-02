import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Корневая директория репозитория
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

# Загружаем переменные окружения в порядке приоритета
for env_name in ["backend/conf.env", "conf.env", ".env"]:
    env_path = ROOT_DIR / env_name
    if env_path.is_file():
        load_dotenv(env_path, override=True)

load_dotenv(override=False)


class Settings(BaseModel):
    app_title: str = "Устное собеседование по русскому языку (ОГЭ 9 класс)"
    app_version: str = "1.0.0"

    host: str = Field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", 8000)))

    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))

    http_proxy: Optional[str] = Field(
        default_factory=lambda: os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    )
    https_proxy: Optional[str] = Field(
        default_factory=lambda: os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    )

    root_dir: Path = ROOT_DIR
    data_dir: Path = ROOT_DIR / "data"
    tasks_dir: Path = ROOT_DIR / "data" / "tasks"
    frontend_dir: Path = ROOT_DIR / "frontend"

    def apply_proxy(self):
        proxy = self.http_proxy or self.https_proxy
        if proxy:
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy
            os.environ["HTTP_PROXY"] = proxy
            os.environ["HTTPS_PROXY"] = proxy


settings = Settings()
settings.apply_proxy()
