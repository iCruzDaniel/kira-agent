from kira.db.business_repo import BusinessRepository


def test_catalog_lists_services_and_products(repo: BusinessRepository) -> None:
    catalog = repo.list_catalog()
    assert len(catalog["services"]) == 4
    assert len(catalog["products"]) == 3
    assert catalog["services"][0]["price"].startswith("$")


def test_catalog_filters_by_category(repo: BusinessRepository) -> None:
    catalog = repo.list_catalog("Cortes")
    assert catalog["services"]
    assert all(service["category"] == "Cortes" for service in catalog["services"])
    assert catalog["products"] == []


def test_get_service(repo: BusinessRepository) -> None:
    service = repo.get_service(1)
    assert service is not None
    assert service["name"] == "Corte clásico"
    assert repo.get_service(999) is None
