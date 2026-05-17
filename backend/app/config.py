from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_model: str
    app_public_url: str
    app_title: str
    cors_origins: str
    app_dir: Path
    storage_dir: Path
    docs_dir: Path


@lru_cache
def get_settings() -> Settings:
    _load_env_files()
    app_dir = Path(__file__).resolve().parent
    settings = Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        app_public_url=os.getenv("APP_PUBLIC_URL", "http://localhost:8000"),
        app_title=os.getenv("APP_TITLE", "TP-100 Diagnostics Analyzer"),
        cors_origins=os.getenv("CORS_ORIGINS", "*"),
        app_dir=app_dir,
        storage_dir=app_dir / "storage",
        docs_dir=app_dir / "data" / "docs",
    )
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings


def _load_env_files() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
