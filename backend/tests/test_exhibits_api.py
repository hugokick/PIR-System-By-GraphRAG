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
    ids = {item["id"] for item in payload["items"]}
    assert {"lever-play", "pulley-wall"} <= ids
    assert all(item["venue_type"] == "儿童科技馆" for item in payload["items"])
    assert all(any(material["name"] == "金属" for material in item["materials"]) for item in payload["items"])
    assert all(any(interaction["name"] == "机械互动" for interaction in item["interactions"]) for item in payload["items"])


def test_list_exhibits_supports_project_case_filter():
    qinghe_response = client.get("/api/exhibits", params={"project_id": "qinghe-2024"})
    jiangbei_response = client.get("/api/exhibits", params={"project_id": "jiangbei-2022"})

    assert qinghe_response.status_code == 200
    qinghe_payload = qinghe_response.json()
    assert qinghe_payload["total"] >= 2
    assert {"lever-play", "pulley-wall"} <= {item["id"] for item in qinghe_payload["items"]}
    assert all(item["project"]["id"] == "qinghe-2024" for item in qinghe_payload["items"])

    assert jiangbei_response.status_code == 200
    jiangbei_payload = jiangbei_response.json()
    assert jiangbei_payload["total"] >= 1
    assert "water-cycle" in {item["id"] for item in jiangbei_payload["items"]}
    assert all(item["project"]["id"] == "jiangbei-2022" for item in jiangbei_payload["items"])


def test_list_exhibits_supports_review_status_filter():
    pending_response = client.get("/api/exhibits", params={"review_status": "待审核"})
    approved_response = client.get("/api/exhibits", params={"review_status": "已审核"})

    assert pending_response.status_code == 200
    pending_payload = pending_response.json()
    assert pending_payload["total"] >= 1
    assert "pulley-wall" in {item["id"] for item in pending_payload["items"]}
    assert all(item["review_status"] == "待审核" for item in pending_payload["items"])

    assert approved_response.status_code == 200
    approved_payload = approved_response.json()
    assert approved_payload["total"] >= 1
    assert "lever-play" in {item["id"] for item in approved_payload["items"]}
    assert all(item["review_status"] == "已审核" for item in approved_payload["items"])

def test_list_exhibits_supports_tag_filter():
    response = client.get("/api/exhibits", params={"tag": "低预算"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert "pulley-wall" in {item["id"] for item in payload["items"]}
    assert all("低预算" in item["tags"] for item in payload["items"])

def test_list_exhibits_supports_owner_and_supplier_filters():
    owner_response = client.get("/api/exhibits", params={"owner": "青禾儿童科技馆"})
    supplier_response = client.get("/api/exhibits", params={"supplier": "澄境模型"})

    assert owner_response.status_code == 200
    owner_payload = owner_response.json()
    assert owner_payload["total"] >= 2
    assert {"lever-play", "pulley-wall"} <= {item["id"] for item in owner_payload["items"]}
    assert all(item["owner"]["name"] == "青禾儿童科技馆" for item in owner_payload["items"])

    assert supplier_response.status_code == 200
    supplier_payload = supplier_response.json()
    assert supplier_payload["total"] >= 1
    assert "water-cycle" in {item["id"] for item in supplier_payload["items"]}
    assert all(item["supplier"]["name"] == "澄境模型" for item in supplier_payload["items"])


def test_export_exhibits_csv_uses_structured_filters():
    response = client.get(
        "/api/exhibits/export",
        params={"project_id": "jiangbei-2022"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "exhibits.csv" in response.headers["content-disposition"]
    csv_text = response.content.decode("utf-8-sig")

    assert "展项编号,展项名称,类别,主题,适用场馆,造价下限,造价上限" in csv_text
    assert "water-cycle,城市水循环沙盘" in csv_text
    assert "lever-play,杠杆乐园" not in csv_text


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


def test_get_exhibit_graph_can_use_neo4j_demo_service(monkeypatch):
    from app import main
    from app.schemas import GraphNode, GraphResponse

    class StubNeo4jService:
        def __init__(self, exhibits):
            self.exhibits = list(exhibits)

        def get_exhibit_graph(self, exhibit_id: str) -> GraphResponse:
            return GraphResponse(
                nodes=[GraphNode(id=f"neo4j:{exhibit_id}", label="Neo4j graph", type="neo4j")],
                edges=[],
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(main, "create_neo4j_demo_graph_service", lambda exhibits: StubNeo4jService(exhibits))

    response = client.get("/api/exhibits/lever-play/graph")

    assert response.status_code == 200
    assert response.json()["nodes"] == [
        {"id": "neo4j:lever-play", "label": "Neo4j graph", "type": "neo4j"}
    ]


def test_get_exhibit_graph_prefers_repository_kg_projection(monkeypatch):
    from app import main
    from app.repository import seed_exhibits
    from app.schemas import GraphEdge, GraphNode, GraphResponse

    class StubRepository:
        def get_exhibit(self, exhibit_id: str):
            return seed_exhibits[0] if exhibit_id == "lever-play" else None

        def get_exhibit_graph(self, exhibit_id: str) -> GraphResponse:
            assert exhibit_id == "lever-play"
            return GraphResponse(
                nodes=[
                    GraphNode(id="exhibit:lever-play", label="杠杆乐园", type="exhibit"),
                    GraphNode(id="material:metal", label="金属", type="material"),
                ],
                edges=[
                    GraphEdge(
                        source="exhibit:lever-play",
                        target="material:metal",
                        label="使用材料",
                        type="uses_material",
                    )
                ],
            )

        def list_exhibits(self):
            return seed_exhibits

    def fail_if_neo4j_is_used(_):
        raise AssertionError("Neo4j fallback should not be used when repository KG projection is available")

    monkeypatch.setattr(main, "repository", StubRepository())
    monkeypatch.setattr(main, "create_neo4j_demo_graph_service", fail_if_neo4j_is_used)

    response = client.get("/api/exhibits/lever-play/graph")

    assert response.status_code == 200
    payload = response.json()
    assert payload["nodes"] == [
        {"id": "exhibit:lever-play", "label": "杠杆乐园", "type": "exhibit"},
        {"id": "material:metal", "label": "金属", "type": "material"},
    ]
    assert payload["edges"][0]["type"] == "uses_material"


def test_get_exhibit_graph_allows_demo_only_exhibit(monkeypatch):
    from app import main
    from app.schemas import GraphNode, GraphResponse

    class StubNeo4jService:
        def get_exhibit_graph(self, exhibit_id: str) -> GraphResponse:
            if exhibit_id == "space-dome":
                return GraphResponse(
                    nodes=[GraphNode(id="exhibit:space-dome", label="星际穹幕影院", type="exhibit")],
                    edges=[],
                )
            return GraphResponse(nodes=[], edges=[])

        def close(self) -> None:
            return None

    monkeypatch.setattr(main, "create_neo4j_demo_graph_service", lambda exhibits: StubNeo4jService())

    response = client.get("/api/exhibits/space-dome/graph")

    assert response.status_code == 200
    assert response.json()["nodes"] == [
        {"id": "exhibit:space-dome", "label": "星际穹幕影院", "type": "exhibit"}
    ]


def test_unknown_exhibit_returns_404():
    response = client.get("/api/exhibits/not-found")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "NotFound"


def test_get_neo4j_demo_graph_returns_full_demo_graph(monkeypatch):
    from app import main
    from app.schemas import GraphEdge, GraphNode, GraphResponse

    class StubNeo4jService:
        def __init__(self):
            self.closed = False

        def get_demo_graph(self) -> GraphResponse:
            return GraphResponse(
                nodes=[
                    GraphNode(id="exhibit:lever-play", label="Lever Play", type="exhibit"),
                    GraphNode(id="exhibit:space-dome", label="Space Dome", type="exhibit"),
                    GraphNode(id="supplier:qisi", label="Qisi", type="supplier"),
                ],
                edges=[
                    GraphEdge(
                        source="exhibit:lever-play",
                        target="supplier:qisi",
                        label="supplier",
                        type="supplied_by",
                    )
                ],
            )

        def close(self) -> None:
            self.closed = True

    service = StubNeo4jService()
    monkeypatch.setattr(main, "create_neo4j_demo_graph_service", lambda exhibits: service)

    response = client.get("/api/neo4j-demo/graph")

    assert response.status_code == 200
    payload = response.json()
    node_ids = {node["id"] for node in payload["nodes"]}
    assert {"exhibit:lever-play", "exhibit:space-dome", "supplier:qisi"} <= node_ids
    assert payload["edges"] == [
        {
            "source": "exhibit:lever-play",
            "target": "supplier:qisi",
            "label": "supplier",
            "type": "supplied_by",
        }
    ]
    assert service.closed


def test_create_exhibit_persists_record_and_relationships():
    payload = {
        "id": "magnet-maze-api-demo",
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
    assert create_response.json()["id"] == "magnet-maze-api-demo"

    detail_response = client.get("/api/exhibits/magnet-maze-api-demo")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "磁力迷宫"

    graph_response = client.get("/api/exhibits/magnet-maze-api-demo/graph")
    edge_types = {edge["type"] for edge in graph_response.json()["edges"]}
    assert "has_theme" in edge_types
    assert "similar_to" in edge_types


def test_create_exhibit_rejects_duplicate_id():
    payload = client.get("/api/exhibits/lever-play").json()

    response = client.post("/api/exhibits", json=payload, headers=EDITOR_HEADERS)

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "Conflict"


def test_create_exhibit_rejects_unknown_related_exhibit_ids():
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["id"] = "invalid-create-relation-demo"
    payload["related_exhibit_ids"] = ["missing-related-exhibit"]

    response = client.post("/api/exhibits", json=payload, headers=EDITOR_HEADERS)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "InvalidRelatedExhibits"
    assert detail["details"] == {
        "id": "invalid-create-relation-demo",
        "invalid_ids": ["missing-related-exhibit"],
    }
    assert client.get("/api/exhibits/invalid-create-relation-demo").status_code == 404


def test_update_exhibit_replaces_existing_record():
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["id"] = "update-replace-demo"
    payload["name"] = "更新替换示例"
    payload["related_exhibit_ids"] = []
    create_response = client.post("/api/exhibits", json=payload, headers=EDITOR_HEADERS)
    assert create_response.status_code == 201

    try:
        update_payload = create_response.json()
        update_payload["name"] = "更新替换示例 Pro"
        update_payload["materials"] = [{"id": "steel", "name": "钢结构"}]

        response = client.put("/api/exhibits/update-replace-demo", json=update_payload, headers=EDITOR_HEADERS)

        assert response.status_code == 200
        assert response.json()["name"] == "更新替换示例 Pro"
        assert response.json()["materials"] == [{"id": "steel", "name": "钢结构"}]
    finally:
        client.delete("/api/exhibits/update-replace-demo", headers=ADMIN_HEADERS)


def test_editor_create_exhibit_cannot_self_approve_review_status():
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["id"] = "editor-create-review-demo"
    payload["status"] = "概念方案"
    payload["review_status"] = "已审核"
    payload["related_exhibit_ids"] = []

    response = client.post("/api/exhibits", json=payload, headers=EDITOR_HEADERS)

    assert response.status_code == 201
    assert response.json()["review_status"] == "待审核"

    client.delete("/api/exhibits/editor-create-review-demo", headers=ADMIN_HEADERS)


def test_editor_update_exhibit_cannot_change_review_status():
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["name"] = "滑轮挑战墙 编辑稿"
    payload["review_status"] = "已审核"

    response = client.put("/api/exhibits/pulley-wall", json=payload, headers=EDITOR_HEADERS)

    assert response.status_code == 200
    assert response.json()["name"] == "滑轮挑战墙 编辑稿"
    assert response.json()["review_status"] == "待审核"


def test_editor_update_approved_exhibit_moves_back_to_pending_review():
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["id"] = "editor-approved-review-reset-demo"
    payload["name"] = "已审核编辑回审示例"
    payload["review_status"] = "已审核"
    payload["related_exhibit_ids"] = []

    create_response = client.post(
        "/api/exhibits",
        json=payload,
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 201
    assert create_response.json()["review_status"] == "已审核"

    try:
        update_payload = create_response.json()
        update_payload["name"] = "编辑员修改后的待审稿"
        update_payload["review_status"] = "已审核"

        response = client.put(
            "/api/exhibits/editor-approved-review-reset-demo",
            json=update_payload,
            headers=EDITOR_HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "编辑员修改后的待审稿"
        assert response.json()["review_status"] == "待审核"

        audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
        entries = audit_response.json()["items"]
        assert any(
            entry["action"] == "update_exhibit"
            and entry["resource_id"] == "editor-approved-review-reset-demo"
            and "审核状态已回到待审核" in entry["summary"]
            and "Updated exhibit" not in entry["summary"]
            for entry in entries
        )
    finally:
        cleanup_payload = client.get("/api/exhibits/editor-approved-review-reset-demo").json()
        cleanup_payload["review_status"] = "待审核"
        cleanup_payload["status"] = "制作中"
        client.put(
            "/api/exhibits/editor-approved-review-reset-demo",
            json=cleanup_payload,
            headers=ADMIN_HEADERS,
        )
        client.delete("/api/exhibits/editor-approved-review-reset-demo", headers=ADMIN_HEADERS)


def test_update_exhibit_rejects_self_and_unknown_related_exhibit_ids():
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["related_exhibit_ids"] = ["pulley-wall", "missing-related-exhibit"]

    response = client.put("/api/exhibits/pulley-wall", json=payload, headers=EDITOR_HEADERS)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "InvalidRelatedExhibits"
    assert detail["details"] == {
        "id": "pulley-wall",
        "invalid_ids": ["pulley-wall", "missing-related-exhibit"],
    }
    assert "missing-related-exhibit" not in client.get("/api/exhibits/pulley-wall").json()["related_exhibit_ids"]


def test_update_exhibit_relationships_refreshes_graph_edges():
    payload = client.get("/api/exhibits/pulley-wall").json()
    payload["id"] = "relation-put-demo"
    payload["related_exhibit_ids"] = []
    create_response = client.post("/api/exhibits", json=payload, headers=EDITOR_HEADERS)
    assert create_response.status_code == 201

    try:
        update_payload = create_response.json()
        update_payload["related_exhibit_ids"] = ["water-cycle"]

        response = client.put("/api/exhibits/relation-put-demo", json=update_payload, headers=EDITOR_HEADERS)
        assert response.status_code == 200

        graph_response = client.get("/api/exhibits/relation-put-demo/graph")
        outgoing_similar_edges = [
            edge
            for edge in graph_response.json()["edges"]
            if edge["type"] == "similar_to" and edge["source"] == "exhibit:relation-put-demo"
        ]

        assert outgoing_similar_edges == [
            {
                "source": "exhibit:relation-put-demo",
                "target": "exhibit:water-cycle",
                "label": "相似展项",
                "type": "similar_to",
            }
        ]
    finally:
        client.delete("/api/exhibits/relation-put-demo", headers=ADMIN_HEADERS)


def test_patch_related_exhibits_updates_curated_similarity_graph_edges():
    create_payload = client.get("/api/exhibits/pulley-wall").json()
    create_payload["id"] = "relation-editor-demo"
    create_payload["related_exhibit_ids"] = []
    create_response = client.post("/api/exhibits", json=create_payload, headers=EDITOR_HEADERS)
    assert create_response.status_code == 201

    try:
        response = client.patch(
            "/api/exhibits/relation-editor-demo/related-exhibits",
            json={"related_exhibit_ids": ["lever-play", "water-cycle"]},
            headers=EDITOR_HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["related_exhibit_ids"] == ["lever-play", "water-cycle"]

        graph_response = client.get("/api/exhibits/relation-editor-demo/graph")
        similar_targets = [
            edge["target"]
            for edge in graph_response.json()["edges"]
            if edge["type"] == "similar_to"
        ]
        assert similar_targets == ["exhibit:lever-play", "exhibit:water-cycle"]
    finally:
        client.delete("/api/exhibits/relation-editor-demo", headers=ADMIN_HEADERS)


def test_editor_patch_related_exhibits_moves_approved_exhibit_back_to_pending_review():
    create_payload = client.get("/api/exhibits/pulley-wall").json()
    create_payload["id"] = "relation-review-reset-demo"
    create_payload["status"] = "制作中"
    create_payload["review_status"] = "已审核"
    create_payload["related_exhibit_ids"] = []
    create_response = client.post("/api/exhibits", json=create_payload, headers=ADMIN_HEADERS)
    assert create_response.status_code == 201
    assert create_response.json()["review_status"] == "已审核"

    try:
        response = client.patch(
            "/api/exhibits/relation-review-reset-demo/related-exhibits",
            json={"related_exhibit_ids": ["water-cycle"]},
            headers=EDITOR_HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["review_status"] == "待审核"
        assert response.json()["related_exhibit_ids"] == ["water-cycle"]

        audit_response = client.get("/api/admin/audit-logs", headers=ADMIN_HEADERS)
        entries = audit_response.json()["items"]
        assert any(
            entry["actor_role"] == "editor"
            and entry["action"] == "update_exhibit_relations"
            and entry["resource_id"] == "relation-review-reset-demo"
            and "更新相似关系 relation-review-reset-demo: water-cycle" in entry["summary"]
            and "审核状态已回到待审核" in entry["summary"]
            for entry in entries
        )
    finally:
        cleanup_payload = client.get("/api/exhibits/relation-review-reset-demo").json()
        cleanup_payload["status"] = "制作中"
        cleanup_payload["review_status"] = "待审核"
        client.put("/api/exhibits/relation-review-reset-demo", json=cleanup_payload, headers=ADMIN_HEADERS)
        client.delete("/api/exhibits/relation-review-reset-demo", headers=ADMIN_HEADERS)


def test_get_exhibit_graph_includes_incoming_similarity_edges():
    create_payload = client.get("/api/exhibits/pulley-wall").json()
    create_payload["id"] = "incoming-relation-demo"
    create_payload["related_exhibit_ids"] = ["lever-play"]
    create_response = client.post("/api/exhibits", json=create_payload, headers=EDITOR_HEADERS)
    assert create_response.status_code == 201

    try:
        graph_response = client.get("/api/exhibits/lever-play/graph")

        assert graph_response.status_code == 200
        assert any(
            edge["source"] == "exhibit:incoming-relation-demo"
            and edge["target"] == "exhibit:lever-play"
            and edge["type"] == "similar_to"
            for edge in graph_response.json()["edges"]
        )
        assert any(
            node["id"] == "exhibit:incoming-relation-demo"
            for node in graph_response.json()["nodes"]
        )
    finally:
        client.delete("/api/exhibits/incoming-relation-demo", headers=ADMIN_HEADERS)


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
