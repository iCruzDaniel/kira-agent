"""Memoria de largo plazo en SQLite, aislada por cliente o sesión."""

from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from strands.memory.extraction.types import ExtractionConfig
from strands.memory.types import AddMessagesContext, MemoryEntry, SearchOptions
from strands.types.content import Message
from strands.types.tools import AgentTool

from kira.db.connection import read_connection, transaction
from kira.time_utils import now_iso

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(_normalize(text)) if len(token) > 1}


class SQLiteMemoryStore:
    """Implementa el protocolo `MemoryStore` sobre la tabla `memory_entries`."""

    name: str = "kira_memory"
    description: str | None = "Preferencias, datos de contacto y contexto del cliente."
    max_search_results: int | None = 5
    writable: bool = True
    extraction: ExtractionConfig | bool | None = False

    def __init__(self, db_path: Path, scope: str) -> None:
        self.db_path = db_path
        self.scope = scope

    async def initialize(self) -> None:
        return None

    async def search(
        self, query: str, options: SearchOptions | None = None
    ) -> list[MemoryEntry]:
        limit = self.max_search_results or 5
        if options:
            limit = int(options.get("max_search_results") or limit)
        return await asyncio.to_thread(self._search_sync, query, limit)

    def _search_sync(self, query: str, limit: int) -> list[MemoryEntry]:
        query_tokens = _tokens(query)
        with read_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT content, metadata_json, created_at FROM memory_entries "
                "WHERE scope = ? ORDER BY id DESC LIMIT 200",
                (self.scope,),
            ).fetchall()

        if not query_tokens:
            return [
                MemoryEntry(
                    content=row["content"],
                    metadata=json.loads(row["metadata_json"]),
                )
                for row in rows[:limit]
            ]

        scored: list[tuple[float, MemoryEntry]] = []
        for row in rows:
            overlap = query_tokens & _tokens(row["content"])
            if not overlap:
                continue
            score = len(overlap) / (len(query_tokens) ** 0.5)
            scored.append(
                (
                    score,
                    MemoryEntry(
                        content=row["content"],
                        metadata=json.loads(row["metadata_json"]),
                    ),
                )
            )
        scored.sort(key=lambda item: -item[0])
        return [entry for _, entry in scored[:limit]]

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        await asyncio.to_thread(self._add_sync, content, metadata or {})

    async def add_messages(
        self,
        messages: list[Message],
        context: AddMessagesContext | None = None,
    ) -> None:
        for message in messages:
            text = " ".join(
                str(block.get("text", ""))
                for block in message.get("content", [])
                if isinstance(block, dict)
            ).strip()
            if text:
                await self.add(text, {"role": message.get("role", "unknown")})

    def _add_sync(self, content: str, metadata: dict[str, Any]) -> None:
        now = now_iso()
        with transaction(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memory_entries(scope, content, metadata_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self.scope, content, json.dumps(metadata, ensure_ascii=False), now, now),
            )

    def get_tools(self) -> list[AgentTool]:
        return []
