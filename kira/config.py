"""Configuración central de Kira, leída desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value).expanduser() if value else default


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de una instancia de Kira."""

    db1_path: Path
    db2_path: Path
    timezone: str
    business_name: str
    agent_id: str
    api_host: str
    api_port: int
    log_level: str


def get_settings() -> Settings:
    """Construye la configuración y garantiza que exista el directorio de datos."""

    data_dir = _env_path("KIRA_DATA_DIR", BASE_DIR / "data")
    data_dir.mkdir(parents=True, exist_ok=True)

    db1_path = _env_path("KIRA_DB1_PATH", data_dir / "db_1_business.sqlite3")
    db2_path = _env_path("KIRA_DB2_PATH", data_dir / "db_2_sessions.sqlite3")
    db1_path.parent.mkdir(parents=True, exist_ok=True)
    db2_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        db1_path=db1_path,
        db2_path=db2_path,
        timezone=os.getenv("KIRA_TIMEZONE", "America/Bogota"),
        business_name=os.getenv("KIRA_BUSINESS_NAME", "Estudio Kira"),
        agent_id=os.getenv("KIRA_AGENT_ID", "kira"),
        api_host=os.getenv("KIRA_HOST", "0.0.0.0"),
        api_port=int(os.getenv("KIRA_PORT", "8000")),
        log_level=os.getenv("KIRA_LOG_LEVEL", "INFO").upper(),
    )
