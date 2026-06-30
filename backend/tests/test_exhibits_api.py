from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

ADMIN_HEADERS = {"X-User-Role": "admin"}
EDITOR_HEADERS = {"X-User-Role": "editor"}


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


def test_create_exhibit_persists_record_and_relationships():
    payload = {
        "id": "magnet-maze",
        "name": "磁力迷宫",
        "category": "基础科学",
        "theme": {"id": "electromagnetism", "name": "电磁学"},
        "venue_type": "儿童科技馆",
        "budget_min": 180000,
        "budget_max": 320000,
        "materials": [{"id": "acrylic", "name": "亚克力"}],
        "dimensions": "3600x1800x1800mm",
        "interactions": [{"id": "hands-on", "name": "动手实验"}],
        "supplier": {"id": "qisi", "name": "启思互动工坊"},
        "project": {"id": "qinghe-2024", "name": "青禾儿童科技馆更新项目"},
        "owner": {"id": "qinghe-owner", "name": "青禾儿童科技馆"},
        "project_year": 2024,
        "status": "概念方案",
        "description": "通过磁铁和轨道迷宫演示磁力吸引与排斥。",
        "tags": ["低龄儿童", "电磁学"],
        "media_assets": [],
        "documents": [],
        "related_exhibit_ids": ["lever-play"],
    }

    create_response = client.post("/api/exhibits", json=payload, headers=EDITOR_HEADERS)
    assert create_response.status_code == 201
    assert create_response.json()["id"] == "magnet-maze"

    detail_response = client.get("/api/exhibits/magnet-maze")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "磁力迷宫"

    graph_response = client.get("/api/exhibits/magnet-maze/graph")
    edge_types = {edge["type"] for edge in graph_response.json()["edges"]}
    assert "has_theme" in edge_types
    assert "similar_to" in edge_types


def test_create_exhibit_rejects_duplicate_id():
    payload = client.get("/api/exhibits/lever-play").json()

    response = client.post("/api/exhibits", json=payload, headers=EDITOR_HEADERS)

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "Conflict"


def test_update_exhibit_replaces_existing_record():
    payload = client.get("/api/exhibits/lever-play").json()
    payload["name"] = "杠杆乐园 Pro"
    payload["materials"] = [{"id": "steel", "name": "钢结构"}]

    response = client.put("/api/exhibits/lever-play", json=payload, headers=EDITOR_HEADERS)

    assert response.status_code == 200
    assert response.json()["name"] == "杠杆乐园 Pro"
    assert response.json()["materials"] == [{"id": "steel", "name": "钢结构"}]


def test_update_exhibit_relationships_refreshes_graph_edges():
    payload = client.get("/api/exhibits/lever-play").json()
    payload["related_exhibit_ids"] = ["water-cycle"]

    response = client.put("/api/exhibits/lever-play", json=payload, headers=EDITOR_HEADERS)
    assert response.status_code == 200

    graph_response = client.get("/api/exhibits/lever-play/graph")
    similar_edges = [
        edge
        for edge in graph_response.json()["edges"]
        if edge["type"] == "similar_to"
    ]

    assert similar_edges == [
        {
            "source": "exhibit:lever-play",
            "target": "exhibit:water-cycle",
            "label": "相似展项",
            "type": "similar_to",
        }
    ]


def test_delete_exhibit_soft_removes_from_list_and_detail():
    create_payload = client.get("/api/exhibits/pulley-wall").json()
    create_payload["id"] = "delete-me"
    client.post("/api/exhibits", json=create_payload, headers=EDITOR_HEADERS)

    delete_response = client.delete("/api/exhibits/delete-me", headers=ADMIN_HEADERS)
    assert delete_response.status_code == 204

    detail_response = client.get("/api/exhibits/delete-me")
    assert detail_response.status_code == 404

    list_response = client.get("/api/exhibits")
    ids = {item["id"] for item in list_response.json()["items"]}
    assert "delete-me" not in ids
