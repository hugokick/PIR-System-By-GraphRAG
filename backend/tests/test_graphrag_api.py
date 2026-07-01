from fastapi.testclient import TestClient

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
