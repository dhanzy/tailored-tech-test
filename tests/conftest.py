import pytest
from fastapi.testclient import TestClient

from cache_service.api import create_app, get_transformer
from cache_service.config import ServiceSettings


class CountingTransformer:
    """Records every call so tests can assert how often the 'external service' is hit."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, value: str) -> str:
        self.calls.append(value)
        return value.upper()


@pytest.fixture
def transformer() -> CountingTransformer:
    return CountingTransformer()


@pytest.fixture
def client(tmp_path, transformer):
    app = create_app(ServiceSettings(database_url=f"sqlite:///{tmp_path / 'test.db'}"))
    app.dependency_overrides[get_transformer] = lambda: transformer
    with TestClient(app) as test_client:  # context manager runs the lifespan (creates tables)
        yield test_client
