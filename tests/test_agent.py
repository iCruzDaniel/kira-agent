from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

from pydantic import BaseModel
from strands.models.model import Model
from strands.types.streaming import (
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    MessageStartEvent,
    MessageStopEvent,
    StreamEvent,
)

from kira.agent.kira import build_agent
from kira.config import Settings
from kira.db.session_repository import SQLiteSessionRepository


class FakeModel(Model):
    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self._config

    async def structured_output(
        self,
        output_model: type[BaseModel],
        prompt: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"output": output_model()}

    async def stream(
        self,
        messages: Any,
        tool_specs: Any = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(messageStart=MessageStartEvent(role="assistant"))
        yield StreamEvent(contentBlockStart=ContentBlockStartEvent(start={}))
        yield StreamEvent(contentBlockDelta=ContentBlockDeltaEvent(delta={"text": "Hola"}))
        yield StreamEvent(contentBlockStop=ContentBlockStopEvent())
        yield StreamEvent(messageStop=MessageStopEvent(stopReason="end_turn"))


def test_build_agent_registers_tools_and_session(settings: Settings) -> None:
    agent = build_agent("s1", "customer-1", model=FakeModel(), settings=settings)

    assert agent.agent_id == "kira"
    assert agent.name == "Kira"
    assert "faq_search" in agent.tool_names
    assert "create_quote" in agent.tool_names
    assert "check_availability" in agent.tool_names
    assert "book_appointment" in agent.tool_names
    assert "create_order" in agent.tool_names
    assert "search_memory" in agent.tool_names
    assert "add_memory" in agent.tool_names

    session = SQLiteSessionRepository(settings.db2_path).read_session("s1")
    assert session is not None


def test_agent_persists_session_messages(settings: Settings) -> None:
    agent = build_agent("s2", "customer-2", model=FakeModel(), settings=settings)
    result = agent("hola")

    assert "Hola" in str(result)
    messages = SQLiteSessionRepository(settings.db2_path).list_messages("s2", "kira")
    assert messages
    assert messages[-1].to_message()["role"] == "assistant"
