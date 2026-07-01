from fastapi.testclient import TestClient

from app.repository import seed_exhibits
from app.main import app


client = TestClient(app)


def test_graphrag_search_returns_contract_shape():
    response = client.post("/api/graphrag/search", json={"query": "力学", "top_k": 2})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"query", "total", "items"}
    assert isinstance(payload["items"], list)


def test_graphrag_answer_returns_grounded_shape():
    response = client.post("/api/graphrag/answer", json={"query": "杠杆", "top_k": 1})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"query", "answer", "citations", "items"}


def test_graphrag_search_uses_contract_results_without_reimplementing_scoring(monkeypatch):
    from app.services import graphrag as graphrag_service

    called = {}

    def fake_query_contract(query_input, exhibits, snapshot=None):
        called["query_text"] = query_input.query_text
        called["exhibit_count"] = len(exhibits)
        from app.graphrag.contract import KGGraphRAGQueryResult

        return KGGraphRAGQueryResult()

    monkeypatch.setattr(graphrag_service, "query_graphrag_contract", fake_query_contract)

    response = graphrag_service.search_graphrag_context("力学", seed_exhibits, top_k=1)

    assert response.total == 0
    assert called["query_text"] == "力学"
    assert called["exhibit_count"] == len(seed_exhibits)


def test_graphrag_answer_keeps_grounded_numbered_citations():
    response = client.post("/api/graphrag/answer", json={"query": "杠杆乐园 启思互动工坊", "top_k": 1})

    assert response.status_code == 200
    payload = response.json()
    assert "根据库内资料" in payload["answer"]
    assert payload["items"]
    if payload["citations"]:
        assert "[1]" in payload["answer"]
