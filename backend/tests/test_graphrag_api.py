from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_graphrag_search_returns_ranked_hits_with_graph_context_and_citations():
    response = client.post(
        "/api/graphrag/search",
        json={"query": "lever-play", "top_k": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "lever-play"
    assert payload["total"] >= 1

    first = payload["items"][0]
    assert first["exhibit"]["id"] == "lever-play"
    assert first["score"] > 0
    assert first["reasons"]
    assert any(citation["source_type"] == "exhibit" for citation in first["citations"])

    node_ids = {node["id"] for node in first["graph"]["nodes"]}
    edge_types = {edge["type"] for edge in first["graph"]["edges"]}
    assert "exhibit:lever-play" in node_ids
    assert "has_theme" in edge_types


def test_graphrag_answer_uses_search_hits_and_returns_citations():
    response = client.post(
        "/api/graphrag/answer",
        json={"query": "lever-play", "top_k": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "lever-play" in payload["answer"]
    assert payload["citations"]
    assert payload["items"][0]["exhibit"]["id"] == "lever-play"


def test_graphrag_answer_reports_when_no_evidence_is_found():
    response = client.post(
        "/api/graphrag/answer",
        json={"query": "definitely-not-in-library", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["citations"] == []
    assert "No evidence" in payload["answer"]
