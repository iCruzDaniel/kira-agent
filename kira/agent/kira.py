"""Construye una instancia de Kira con sesión y memoria persistentes."""

from __future__ import annotations

from strands import Agent
from strands.memory import MemoryManager
from strands.models.model import Model
from strands.session.repository_session_manager import RepositorySessionManager

from gateway_provider import get_model
from kira.agent.prompts import build_system_prompt
from kira.config import Settings, get_settings
from kira.db.business_repo import BusinessRepository
from kira.db.memory_store import SQLiteMemoryStore
from kira.db.session_repository import SQLiteSessionRepository
from kira.tools import build_tools


def build_agent(
    session_id: str,
    customer_id: str | None = None,
    model: Model | None = None,
    settings: Settings | None = None,
) -> Agent:
    """Crea un agente con tools, sesión SQLite y memoria por cliente/sesión."""

    settings = settings or get_settings()
    repo = BusinessRepository(settings.db1_path, settings.timezone)

    session_repository = SQLiteSessionRepository(settings.db2_path)
    session_manager = RepositorySessionManager(
        session_id=session_id,
        session_repository=session_repository,
    )

    memory_store = SQLiteMemoryStore(
        db_path=settings.db2_path,
        scope=customer_id or session_id,
    )
    memory_manager = MemoryManager(
        stores=[memory_store],
        search_tool_config=True,
        add_tool_config=True,
    )

    return Agent(
        model=model or get_model(),
        tools=build_tools(repo),
        system_prompt=build_system_prompt(settings),
        agent_id=settings.agent_id,
        name="Kira",
        description="Asistente de FAQ, cotizaciones y agendamiento",
        session_manager=session_manager,
        memory_manager=memory_manager,
        callback_handler=None,
    )
