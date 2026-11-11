from __future__ import annotations

from pathlib import Path

import pytest

from kira.config import Settings
from kira.db.business_repo import BusinessRepository
from kira.db.migrate import init_databases


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    settings = Settings(
        db1_path=tmp_path / "db_1_business.sqlite3",
        db2_path=tmp_path / "db_2_sessions.sqlite3",
        timezone="America/Bogota",
        business_name="Estudio Kira",
        agent_id="kira",
        api_host="127.0.0.1",
        api_port=8000,
        log_level="INFO",
    )
    init_databases(settings)
    return settings


@pytest.fixture
def repo(settings: Settings) -> BusinessRepository:
    return BusinessRepository(settings.db1_path, settings.timezone)
