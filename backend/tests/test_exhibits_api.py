from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "exhibit-atlas-api"}


def test_list_exhibits_supports_structured_filters():
    response = client.get(
        "/api/exhibits",
        params={
            "venue_type": "儿童科技馆",
            "material": "金属",
            "interaction": "机械互动",
            "budget_min": 200000,
            "budget_max": 500000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [item["id"] for item in payload["items"]] == ["lever-play", "pulley-wall"]


def test_get_exhibit_detail_includes_documents_and_media():
    response = client.get("/api/exhibits/lever-play")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "lever-play"
    assert payload["owner"]["name"] == "青禾儿童科技馆"
    assert payload["supplier"]["name"] == "启思互动工坊"
    assert payload["media_assets"][0]["type"] == "image"
    assert payload["documents"][0]["file_type"] == "pdf"


def test_get_exhibit_graph_returns_nodes_and_edges_from_relationships():
    response = client.get("/api/exhibits/lever-play/graph")

    assert response.status_code == 200
    payload = response.json()
    node_ids = {node["id"] for node in payload["nodes"]}
    edge_types = {edge["type"] for edge in payload["edges"]}

    assert "exhibit:lever-play" in node_ids
    assert "project:qinghe-2024" in node_ids
    assert "material:metal" in node_ids
    assert "interaction:mechanical" in node_ids
    assert "belongs_to_project" in edge_types
    assert "uses_material" in edge_types
    assert "has_interaction" in edge_types
    assert "similar_to" in edge_types


def test_unknown_exhibit_returns_404():
    response = client.get("/api/exhibits/not-found")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "NotFound"
