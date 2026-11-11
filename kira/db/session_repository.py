"""Implementación SQLite de `SessionRepository` para Strands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from strands.session.session_repository import SessionRepository
from strands.types.session import (
    Session,
    SessionAgent,
    SessionMessage,
    SessionType,
    decode_bytes_values,
    encode_bytes_values,
)

from kira.db.connection import read_connection, transaction


class SQLiteSessionRepository(SessionRepository):
    """Persiste sesiones, agentes y mensajes en db_2."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def create_session(self, session: Session, **kwargs: Any) -> Session:
        with transaction(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(session_id, session_type, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    session.session_id,
                    session.session_type.value,
                    session.created_at,
                    session.updated_at,
                ),
            )
        return session

    def read_session(self, session_id: str, **kwargs: Any) -> Session | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT session_id, session_type, created_at, updated_at "
                "FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return Session(
            session_id=row["session_id"],
            session_type=SessionType(row["session_type"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        self._upsert_agent(session_id, session_agent)

    def read_agent(self, session_id: str, agent_id: str, **kwargs: Any) -> SessionAgent | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT agent_id, state_json, conversation_manager_state_json, "
                "internal_state_json, created_at, updated_at FROM session_agents "
                "WHERE session_id = ? AND agent_id = ?",
                (session_id, agent_id),
            ).fetchone()
        if not row:
            return None
        return SessionAgent(
            agent_id=row["agent_id"],
            state=decode_bytes_values(json.loads(row["state_json"])),
            conversation_manager_state=decode_bytes_values(
                json.loads(row["conversation_manager_state_json"])
            ),
            _internal_state=decode_bytes_values(json.loads(row["internal_state_json"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def update_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        self._upsert_agent(session_id, session_agent)

    def _upsert_agent(self, session_id: str, session_agent: SessionAgent) -> None:
        with transaction(self.db_path) as conn:
            conn.execute(
                "INSERT INTO session_agents(session_id, agent_id, state_json, "
                "conversation_manager_state_json, internal_state_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id, agent_id) DO UPDATE SET "
                "state_json = excluded.state_json, "
                "conversation_manager_state_json = excluded.conversation_manager_state_json, "
                "internal_state_json = excluded.internal_state_json, "
                "updated_at = excluded.updated_at",
                (
                    session_id,
                    session_agent.agent_id,
                    json.dumps(encode_bytes_values(session_agent.state), ensure_ascii=False),
                    json.dumps(
                        encode_bytes_values(session_agent.conversation_manager_state),
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        encode_bytes_values(session_agent._internal_state), ensure_ascii=False
                    ),
                    session_agent.created_at,
                    session_agent.updated_at,
                ),
            )

    def create_message(
        self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any
    ) -> None:
        redact = (
            json.dumps(encode_bytes_values(session_message.redact_message), ensure_ascii=False)
            if session_message.redact_message is not None
            else None
        )
        with transaction(self.db_path) as conn:
            conn.execute(
                "INSERT INTO session_messages(session_id, agent_id, message_id, message_json, "
                "redact_message_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    agent_id,
                    session_message.message_id,
                    json.dumps(session_message.to_dict(), ensure_ascii=False),
                    redact,
                    session_message.created_at,
                    session_message.updated_at,
                ),
            )

    def read_message(
        self, session_id: str, agent_id: str, message_id: int, **kwargs: Any
    ) -> SessionMessage | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT message_json FROM session_messages "
                "WHERE session_id = ? AND agent_id = ? AND message_id = ?",
                (session_id, agent_id, message_id),
            ).fetchone()
        if not row:
            return None
        return SessionMessage.from_dict(json.loads(row["message_json"]))

    def update_message(
        self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any
    ) -> None:
        redact = (
            json.dumps(encode_bytes_values(session_message.redact_message), ensure_ascii=False)
            if session_message.redact_message is not None
            else None
        )
        with transaction(self.db_path) as conn:
            conn.execute(
                "UPDATE session_messages SET message_json = ?, redact_message_json = ?, "
                "updated_at = ? WHERE session_id = ? AND agent_id = ? AND message_id = ?",
                (
                    json.dumps(session_message.to_dict(), ensure_ascii=False),
                    redact,
                    session_message.updated_at,
                    session_id,
                    agent_id,
                    session_message.message_id,
                ),
            )

    def list_messages(
        self,
        session_id: str,
        agent_id: str,
        limit: int | None = None,
        offset: int = 0,
        **kwargs: Any,
    ) -> list[SessionMessage]:
        sql = (
            "SELECT message_json FROM session_messages "
            "WHERE session_id = ? AND agent_id = ? ORDER BY message_id"
        )
        params: list[Any] = [session_id, agent_id]
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset:
            sql += " LIMIT -1 OFFSET ?"
            params.append(offset)
        with read_connection(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [SessionMessage.from_dict(json.loads(row["message_json"])) for row in rows]
