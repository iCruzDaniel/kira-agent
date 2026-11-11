from kira.db.business_repo import BusinessRepository


def test_search_faq_finds_horario(repo: BusinessRepository) -> None:
    results = repo.search_faq("¿Cuál es el horario de atención?")
    assert results
    assert any("horario" in item["question"].lower() for item in results)


def test_search_faq_empty_query(repo: BusinessRepository) -> None:
    assert repo.search_faq("") == []


def test_search_faq_respects_limit(repo: BusinessRepository) -> None:
    results = repo.search_faq("servicio cita producto", limit=2)
    assert len(results) <= 2
