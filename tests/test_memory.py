import pytest

from kira.config import Settings
from kira.db.memory_store import SQLiteMemoryStore


@pytest.mark.asyncio
async def test_memory_add_and_search(settings: Settings) -> None:
    store = SQLiteMemoryStore(settings.db2_path, scope="customer-1")
    await store.add("Prefiere citas por la mañana", {"kind": "preference"})
    results = await store.search("mañana")
    assert results
    assert "mañana" in results[0].content
    assert results[0].metadata == {"kind": "preference"}


@pytest.mark.asyncio
async def test_memory_is_scoped(settings: Settings) -> None:
    first = SQLiteMemoryStore(settings.db2_path, scope="customer-1")
    second = SQLiteMemoryStore(settings.db2_path, scope="customer-2")
    await first.add("Cliente uno", {})
    assert await second.search("cliente") == []
