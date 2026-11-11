"""Aplicación FastAPI de Kira."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, Protocol
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from kira.agent.kira import build_agent
from kira.api.schemas import ChatRequest, ChatResponse
from kira.config import Settings, get_settings
from kira.db.business_repo import BusinessRepository
from kira.db.connection import read_connection
from kira.db.migrate import init_databases


class ChatAgent(Protocol):
    async def invoke_async(self, prompt: str) -> Any: ...


AgentFactory = Callable[..., ChatAgent]


def _database_ok(path: Any) -> bool:
    try:
        with read_connection(path) as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


def create_app(
    settings: Settings | None = None,
    agent_factory: AgentFactory = build_agent,
) -> FastAPI:
    settings = settings or get_settings()
    repo = BusinessRepository(settings.db1_path, settings.timezone)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_databases(settings)
        yield

    app = FastAPI(
        title="Kira",
        version="0.1.0",
        description="Agente de FAQ, cotizaciones y agendamiento",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repo = repo
    app.state.agent_factory = agent_factory

    @app.get("/health")
    def health() -> dict[str, Any]:
        db1 = _database_ok(settings.db1_path)
        db2 = _database_ok(settings.db2_path)
        return {
            "status": "ok" if db1 and db2 else "degraded",
            "db1": db1,
            "db2": db2,
        }

    @app.get("/faq")
    def faq(
        query: str = Query(min_length=1, max_length=300),
        limit: int = Query(default=5, ge=1, le=10),
    ) -> dict[str, Any]:
        return {"results": repo.search_faq(query, limit)}

    @app.get("/catalog")
    def catalog(category: str | None = Query(default=None, max_length=80)) -> dict[str, Any]:
        return repo.list_catalog(category)

    @app.get("/bookings")
    def bookings(
        date: str | None = Query(default=None, max_length=40),
        status: str | None = Query(default=None, max_length=20),
    ) -> dict[str, Any]:
        return {"bookings": repo.list_bookings(date, status)}

    @app.get("/quotes/{folio}")
    def quote(folio: str) -> dict[str, Any]:
        found = repo.get_quote(folio)
        if not found:
            raise HTTPException(status_code=404, detail=f"No existe la cotización {folio}.")
        return found

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or f"web-{uuid4().hex}"
        try:
            agent = app.state.agent_factory(
                session_id=session_id,
                customer_id=request.customer_id,
                settings=settings,
            )
        except Exception as exc:  # noqa: BLE001 - error de configuración del proveedor
            raise HTTPException(
                status_code=503,
                detail=f"Kira no está configurada para responder: {exc}",
            ) from exc

        try:
            result = await agent.invoke_async(request.message)
        except Exception as exc:  # noqa: BLE001 - error del modelo o de una tool
            raise HTTPException(
                status_code=500,
                detail=f"Error al procesar el mensaje: {exc}",
            ) from exc

        return ChatResponse(session_id=session_id, response=str(result).strip())

    return app


app = create_app()
