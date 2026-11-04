import pytest
from fastapi.testclient import TestClient
from findex.web.app import app, get_engine, app_state

client = TestClient(app)


class MockEngine:
    def __init__(self):
        self.index = {1: "test doc"}

    def search(self, q, k=5, scorer=None):
        class Result:
            doc_id = 1
            title = "Test"
            snippet = "snippet"
            score = 0.99

        return [Result()]


def override_get_engine():
    return MockEngine()


def test_health_unhealthy():
    app_state["engine"] = None
    response = client.get("/health")
    assert response.status_code == 503


def test_health_and_search_success(monkeypatch):
    # Імітуємо завантажений індекс/двигун у стані
    mock_eng = MockEngine()
    app_state["engine"] = mock_eng
    app.dependency_overrides[get_engine] = override_get_engine

    response = client.get("/health")
    assert response.status_code == 200

    response = client.get("/search?q=python")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["results"][0]["doc_id"] == 1

    app.dependency_overrides.clear()
    app_state["engine"] = None