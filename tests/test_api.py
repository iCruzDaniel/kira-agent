from fastapi.testclient import TestClient

from kira.api.app import create_app
from kira.config import Settings


class FakeResult:
    def __str__(self) -> str:
        return "Hola desde Kira"


class FakeAgent:
    async def invoke_async(self, prompt: str) -> FakeResult:
        return FakeResult()


def fake_factory(session_id, customer_id=None, settings=None):
    return FakeAgent()


def test_health(settings: Settings) -> None:
    app = create_app(settings, agent_factory=fake_factory)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_faq_and_catalog(settings: Settings) -> None:
    app = create_app(settings, agent_factory=fake_factory)
    with TestClient(app) as client:
        faq = client.get("/faq", params={"query": "horario"})
        catalog = client.get("/catalog", params={"category": "Cortes"})
    assert faq.status_code == 200
    assert faq.json()["results"]
    assert catalog.status_code == 200
    assert catalog.json()["services"]


def test_chat(settings: Settings) -> None:
    app = create_app(settings, agent_factory=fake_factory)
    with TestClient(app) as client:
        response = client.post(
            "/chat", json={"message": "hola", "session_id": "web-test"}
        )
    assert response.status_code == 200
    assert response.json() == {
        "session_id": "web-test",
        "response": "Hola desde Kira",
    }


def test_chat_reports_configuration_error(settings: Settings) -> None:
    def broken_factory(**kwargs):
        raise ValueError("sin api key")

    app = create_app(settings, agent_factory=broken_factory)
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "hola"})
    assert response.status_code == 503
    assert "sin api key" in response.json()["detail"]


def test_quote_lookup(settings: Settings) -> None:
    app = create_app(settings, agent_factory=fake_factory)
    quote = app.state.repo.create_quote(
        [{"item_type": "service", "item_id": 1, "quantity": 1}],
        customer_name="Ana",
    )
    with TestClient(app) as client:
        found = client.get(f"/quotes/{quote['folio']}")
        missing = client.get("/quotes/COT-NOPE")
    assert found.status_code == 200
    assert found.json()["folio"] == quote["folio"]
    assert missing.status_code == 404
