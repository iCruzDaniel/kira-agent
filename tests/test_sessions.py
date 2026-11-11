from strands.types.session import Session, SessionAgent, SessionMessage, SessionType

from kira.config import Settings
from kira.db.session_repository import SQLiteSessionRepository
from kira.time_utils import now_iso


def test_session_agent_and_message_crud(settings: Settings) -> None:
    repository = SQLiteSessionRepository(settings.db2_path)

    session = Session(session_id="s1", session_type=SessionType.AGENT)
    repository.create_session(session)
    loaded_session = repository.read_session("s1")
    assert loaded_session is not None
    assert loaded_session.session_id == "s1"
    assert repository.read_session("missing") is None

    agent = SessionAgent(
        agent_id="kira",
        state={"turn": 1},
        conversation_manager_state={"window": 10},
        _internal_state={"model_state": {}},
    )
    repository.create_agent("s1", agent)
    loaded = repository.read_agent("s1", "kira")
    assert loaded is not None
    assert loaded.state == {"turn": 1}
    assert loaded.conversation_manager_state == {"window": 10}

    agent.state["turn"] = 2
    agent.updated_at = now_iso()
    repository.update_agent("s1", agent)
    updated_agent = repository.read_agent("s1", "kira")
    assert updated_agent is not None
    assert updated_agent.state["turn"] == 2

    message = SessionMessage.from_message(
        {"role": "user", "content": [{"text": "hola"}]}, 0
    )
    repository.create_message("s1", "kira", message)
    stored = repository.read_message("s1", "kira", 0)
    assert stored is not None
    assert stored.to_message()["content"][0].get("text") == "hola"
    assert len(repository.list_messages("s1", "kira")) == 1

    message.redact_message = {"role": "user", "content": [{"text": "[redactado]"}]}
    message.updated_at = now_iso()
    repository.update_message("s1", "kira", message)
    redacted = repository.read_message("s1", "kira", 0)
    assert redacted is not None
    assert redacted.to_message()["content"][0].get("text") == "[redactado]"


def test_session_message_pagination(settings: Settings) -> None:
    repository = SQLiteSessionRepository(settings.db2_path)
    repository.create_session(Session(session_id="s2", session_type=SessionType.AGENT))
    repository.create_agent(
        "s2",
        SessionAgent(
            agent_id="kira",
            state={},
            conversation_manager_state={},
        ),
    )
    for index in range(3):
        repository.create_message(
            "s2",
            "kira",
            SessionMessage.from_message(
                {"role": "user", "content": [{"text": f"mensaje {index}"}]}, index
            ),
        )
    page = repository.list_messages("s2", "kira", limit=1, offset=1)
    assert len(page) == 1
    assert page[0].to_message()["content"][0].get("text") == "mensaje 1"
