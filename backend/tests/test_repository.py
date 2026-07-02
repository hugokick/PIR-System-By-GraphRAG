from app.repository import ExhibitRepository, seed_exhibits
from app.schemas import DocumentChunk


class FakePostgresRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url


def test_repository_factory_uses_memory_repository_without_database_url():
    from app.repository import create_repository_from_env

    repository = create_repository_from_env({})

    assert isinstance(repository, ExhibitRepository)


def test_seed_exhibits_include_rich_demo_case_library():
    assert len(seed_exhibits) >= 15
    assert len({item.id for item in seed_exhibits}) == len(seed_exhibits)
    assert "space-dome" in {item.id for item in seed_exhibits}
    assert len({item.theme.name for item in seed_exhibits}) >= 8
    assert len({item.venue_type for item in seed_exhibits}) >= 4
    assert any(item.budget_max <= 300000 for item in seed_exhibits)
    assert any(item.budget_min >= 800000 for item in seed_exhibits)


def test_repository_factory_uses_postgres_repository_when_database_url_is_configured():
    from app.repository import create_repository_from_env

    repository = create_repository_from_env(
        {"DATABASE_URL": "postgresql://exhibit:secret@postgres:5432/exhibit_atlas"},
        postgres_repository_cls=FakePostgresRepository,
    )

    assert isinstance(repository, FakePostgresRepository)
    assert repository.database_url == "postgresql://exhibit:secret@postgres:5432/exhibit_atlas"


def test_postgres_repository_schema_uses_jsonb_payload_and_soft_delete():
    from app.repository import PostgresExhibitRepository

    schema_sql = PostgresExhibitRepository.schema_sql()

    assert "payload JSONB NOT NULL" in schema_sql
    assert "deleted_at TIMESTAMPTZ" in schema_sql
    assert "idx_exhibit_records_payload" in schema_sql


def test_postgres_repository_schema_initializes_pgvector_search_embeddings():
    from app.repository import PostgresExhibitRepository

    schema_sql = PostgresExhibitRepository.schema_sql()

    assert "CREATE EXTENSION IF NOT EXISTS vector" in schema_sql
    assert "ADD COLUMN IF NOT EXISTS embedding vector(1536)" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS search_embeddings" in schema_sql
    assert "embedding vector(1536) NOT NULL" in schema_sql
    assert "idx_search_embeddings_embedding" in schema_sql


def test_postgres_repository_schema_initializes_document_chunk_table():
    from app.repository import PostgresExhibitRepository

    schema_sql = PostgresExhibitRepository.schema_sql()

    assert "CREATE TABLE IF NOT EXISTS document_chunks" in schema_sql
    assert "document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE" in schema_sql
    assert "exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE" in schema_sql
    assert "sequence INTEGER NOT NULL" in schema_sql
    assert "text TEXT NOT NULL" in schema_sql
    assert "embedding vector(1536) NOT NULL" in schema_sql
    assert "idx_document_chunks_document_id" in schema_sql


def test_postgres_repository_schema_initializes_kg_projection_tables():
    from app.repository import PostgresExhibitRepository

    schema_sql = PostgresExhibitRepository.schema_sql()

    assert "CREATE TABLE IF NOT EXISTS kg_nodes" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS kg_edges" in schema_sql
    assert "source_refs TEXT[] NOT NULL DEFAULT '{}'" in schema_sql
    assert "idx_kg_edges_source" in schema_sql
    assert "idx_kg_edges_target" in schema_sql


def test_postgres_repository_schema_initializes_domain_entity_tables():
    from app.repository import PostgresExhibitRepository

    schema_sql = PostgresExhibitRepository.schema_sql()

    for table_name in [
        "owners",
        "projects",
        "suppliers",
        "themes",
        "materials",
        "interactions",
        "exhibits",
        "exhibit_materials",
        "exhibit_interactions",
        "media_assets",
        "documents",
        "exhibit_documents",
        "exhibit_relations",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in schema_sql
    assert "review_status TEXT NOT NULL DEFAULT '待审核'" in schema_sql


def test_postgres_repository_maps_json_payload_rows_to_exhibits():
    from app.repository import PostgresExhibitRepository

    repository = PostgresExhibitRepository("postgresql://example", initialize=False)
    row = {"payload": seed_exhibits[0].model_dump(mode="json")}

    exhibit = repository.exhibit_from_row(row)

    assert exhibit.id == "lever-play"
    assert exhibit.theme.name == "力学"
    assert exhibit.related_exhibit_ids == ["pulley-wall"]


def test_postgres_repository_syncs_exhibit_and_document_chunk_embeddings():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [{"payload": exhibit.model_dump(mode="json")}]

    document = seed_exhibits[0].documents[0].model_copy(
        update={
            "chunks": [
                DocumentChunk(
                    id="lever-brief:chunk-1",
                    text="低龄儿童通过配重理解杠杆原理。",
                    sequence=1,
                )
            ]
        }
    )
    exhibit = seed_exhibits[0].model_copy(update={"documents": [document]})
    cursor = RecordingCursor()
    repository = PostgresExhibitRepository("postgresql://example", initialize=False)

    repository._insert_or_restore(cursor, exhibit)

    delete_calls = [call for call in cursor.calls if "DELETE FROM search_embeddings" in call[0]]
    insert_calls = [call for call in cursor.calls if "INSERT INTO search_embeddings" in call[0]]

    assert delete_calls
    assert delete_calls[0][1] == ("exhibit", "lever-play")
    assert len(insert_calls) == 2
    owner_ids = [params[2] for _, params in insert_calls]
    chunk_ids = [params[3] for _, params in insert_calls]
    assert owner_ids == ["lever-play", "lever-play"]
    assert chunk_ids == [None, "lever-brief:chunk-1"]
    assert all(str(params[5]).startswith("[") for _, params in insert_calls)


def test_postgres_repository_uses_provider_aware_embedding_vector(monkeypatch):
    from app import repository as repository_module
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [{"payload": seed_exhibits[0].model_dump(mode="json")}]

    calls = []

    def fake_embedding_vector(text, *, dimensions=1536, provider=None):
        calls.append((text, dimensions, provider))
        return [0.5, 0.25, -0.25]

    monkeypatch.setattr(repository_module, "embedding_provider_from_env", lambda: "configured-provider")
    monkeypatch.setattr(repository_module, "embedding_vector", fake_embedding_vector)

    cursor = RecordingCursor()
    repository = PostgresExhibitRepository("postgresql://example", initialize=False)

    repository._insert_or_restore(cursor, seed_exhibits[0])

    assert calls
    assert all(call[1] == 1536 for call in calls)
    assert all(call[2] == "configured-provider" for call in calls)
    assert any(params[2] == "[0.500000,0.250000,-0.250000]" for _, params in cursor.calls if params)


def test_postgres_repository_backfills_search_embeddings_for_existing_records():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [{"payload": seed_exhibits[0].model_dump(mode="json")}]

    cursor = RecordingCursor()
    repository = PostgresExhibitRepository("postgresql://example", initialize=False)

    repository._backfill_search_embeddings(cursor)

    assert any("SELECT payload FROM exhibit_records" in query for query, _ in cursor.calls)
    assert any("INSERT INTO search_embeddings" in query for query, _ in cursor.calls)


def test_postgres_repository_upsert_refreshes_kg_projection_tables():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [
                {"payload": seed_exhibits[0].model_dump(mode="json")},
                {"payload": seed_exhibits[1].model_dump(mode="json")},
            ]

    cursor = RecordingCursor()
    repository = PostgresExhibitRepository("postgresql://example", initialize=False)

    repository._insert_or_restore(cursor, seed_exhibits[0])

    kg_node_inserts = [call for call in cursor.calls if "INSERT INTO kg_nodes" in call[0]]
    kg_edge_inserts = [call for call in cursor.calls if "INSERT INTO kg_edges" in call[0]]

    assert any("DELETE FROM kg_edges" in query for query, _ in cursor.calls)
    assert any("DELETE FROM kg_nodes" in query for query, _ in cursor.calls)
    assert any(params[0] == "exhibit:lever-play" for _, params in kg_node_inserts)
    assert any(params[1] == "exhibit:lever-play" and params[2] == "exhibit:pulley-wall" for _, params in kg_edge_inserts)


def test_postgres_repository_upsert_refreshes_domain_entity_projection_tables():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [
                {"payload": seed_exhibits[0].model_dump(mode="json")},
                {"payload": seed_exhibits[1].model_dump(mode="json")},
            ]

    cursor = RecordingCursor()
    repository = PostgresExhibitRepository("postgresql://example", initialize=False)

    repository._insert_or_restore(cursor, seed_exhibits[0])

    owner_inserts = [call for call in cursor.calls if "INSERT INTO owners" in call[0]]
    exhibit_inserts = [call for call in cursor.calls if "INSERT INTO exhibits" in call[0]]
    material_link_inserts = [call for call in cursor.calls if "INSERT INTO exhibit_materials" in call[0]]
    relation_inserts = [call for call in cursor.calls if "INSERT INTO exhibit_relations" in call[0]]

    assert any("DELETE FROM exhibit_materials" in query for query, _ in cursor.calls)
    assert any("DELETE FROM suppliers" in query for query, _ in cursor.calls)
    assert any("DELETE FROM materials" in query for query, _ in cursor.calls)
    assert any("DELETE FROM interactions" in query for query, _ in cursor.calls)
    assert any(params[0] == "qinghe-owner" and params[1] == "青禾儿童科技馆" for _, params in owner_inserts)
    assert any(params[0] == "lever-play" and params[3] == "mechanics" for _, params in exhibit_inserts)
    assert any(params == ("lever-play", "metal") for _, params in material_link_inserts)
    assert any(params[1:] == ("lever-play", "pulley-wall", "similar_to") for _, params in relation_inserts)


def test_postgres_repository_domain_projection_canonicalizes_duplicate_lookup_names():
    from app.repository import PostgresExhibitRepository

    canonical = seed_exhibits[0]
    duplicate_supplier = seed_exhibits[1].supplier.model_copy(
        update={
            "id": "legacy-qisi",
            "name": canonical.supplier.name,
        }
    )
    duplicate = seed_exhibits[1].model_copy(update={"supplier": duplicate_supplier})

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [
                {"payload": canonical.model_dump(mode="json")},
                {"payload": duplicate.model_dump(mode="json")},
            ]

    cursor = RecordingCursor()
    repository = PostgresExhibitRepository("postgresql://example", initialize=False)

    repository._sync_domain_projection(cursor, [canonical, duplicate])

    supplier_inserts = [call for call in cursor.calls if "INSERT INTO suppliers" in call[0]]
    exhibit_inserts = [call for call in cursor.calls if "INSERT INTO exhibits" in call[0]]

    assert [params[0] for _, params in supplier_inserts] == [canonical.supplier.id]
    assert all(params[5] == canonical.supplier.id for _, params in exhibit_inserts)


def test_postgres_repository_upsert_refreshes_document_chunk_projection_table():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [{"payload": exhibit.model_dump(mode="json")}]

    document = seed_exhibits[0].documents[0].model_copy(
        update={
            "chunks": [
                DocumentChunk(
                    id="lever-brief:chunk-1",
                    text="低龄儿童通过配重理解杠杆原理。",
                    sequence=1,
                )
            ]
        }
    )
    exhibit = seed_exhibits[0].model_copy(update={"documents": [document]})
    cursor = RecordingCursor()
    repository = PostgresExhibitRepository("postgresql://example", initialize=False)

    repository._insert_or_restore(cursor, exhibit)

    chunk_inserts = [call for call in cursor.calls if "INSERT INTO document_chunks" in call[0]]

    assert any("DELETE FROM document_chunks" in query for query, _ in cursor.calls)
    assert chunk_inserts
    params = chunk_inserts[0][1]
    assert params[:5] == (
        "lever-brief:chunk-1",
        "lever-play",
        "lever-brief",
        1,
        "低龄儿童通过配重理解杠杆原理。",
    )
    assert str(params[5]).startswith("[")


def test_postgres_repository_reads_exhibit_graph_from_domain_relation_tables_first():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []
            self.rows = []
            self.row = None

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            normalized = " ".join(query.split())
            self.calls.append((normalized, params))
            self.row = None
            self.rows = []
            if "FROM exhibits e" in normalized and "JOIN themes t" in normalized:
                self.row = {
                    "id": "lever-play",
                    "name": "杠杆乐园",
                    "theme_id": "mechanics",
                    "theme_name": "力学",
                    "project_id": "qinghe-2024",
                    "project_name": "青禾儿童科技馆更新项目",
                    "owner_id": "qinghe-owner",
                    "owner_name": "青禾儿童科技馆",
                    "supplier_id": "qisi",
                    "supplier_name": "启思互动工坊",
                }
            elif "FROM exhibit_materials" in normalized:
                self.rows = [{"id": "metal", "name": "金属"}]
            elif "FROM exhibit_interactions" in normalized:
                self.rows = [{"id": "mechanical", "name": "机械互动"}]
            elif "FROM exhibit_documents" in normalized:
                self.rows = [{"id": "lever-brief", "name": "杠杆乐园展项说明"}]
            elif "FROM media_assets" in normalized:
                self.rows = [{"id": "lever-render", "name": "展项效果图"}]
            elif "FROM exhibit_relations r" in normalized and "JOIN exhibits target" in normalized:
                self.rows = [{"id": "pulley-wall", "name": "滑轮挑战墙"}]
            elif "FROM exhibit_relations r" in normalized and "JOIN exhibits source" in normalized:
                self.rows = [{"id": "balance-lab", "name": "平衡实验台"}]

        def fetchone(self):
            return self.row

        def fetchall(self):
            return self.rows

    class RecordingConnection:
        def __init__(self, cursor):
            self.cursor_instance = cursor

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_instance

    class RecordingPostgresRepository(PostgresExhibitRepository):
        def __init__(self):
            super().__init__("postgresql://example", initialize=False)
            self.cursor = RecordingCursor()

        def _connect(self):
            return RecordingConnection(self.cursor)

    repository = RecordingPostgresRepository()

    graph = repository.get_exhibit_graph("lever-play")

    assert [node.id for node in graph.nodes] == [
        "exhibit:lever-play",
        "project:qinghe-2024",
        "owner:qinghe-owner",
        "supplier:qisi",
        "theme:mechanics",
        "material:metal",
        "interaction:mechanical",
        "media_asset:lever-render",
        "document:lever-brief",
        "exhibit:pulley-wall",
        "exhibit:balance-lab",
    ]
    assert [
        (edge.source, edge.type, edge.target)
        for edge in graph.edges
    ] == [
        ("exhibit:lever-play", "belongs_to_project", "project:qinghe-2024"),
        ("exhibit:lever-play", "owned_by", "owner:qinghe-owner"),
        ("exhibit:lever-play", "supplied_by", "supplier:qisi"),
        ("exhibit:lever-play", "has_theme", "theme:mechanics"),
        ("exhibit:lever-play", "uses_material", "material:metal"),
        ("exhibit:lever-play", "has_interaction", "interaction:mechanical"),
        ("exhibit:lever-play", "has_media", "media_asset:lever-render"),
        ("exhibit:lever-play", "has_document", "document:lever-brief"),
        ("exhibit:lever-play", "similar_to", "exhibit:pulley-wall"),
        ("exhibit:balance-lab", "similar_to", "exhibit:lever-play"),
    ]
    assert any("FROM exhibits e" in query for query, _ in repository.cursor.calls)
    assert not any("FROM kg_edges" in query for query, _ in repository.cursor.calls)


def test_postgres_repository_reads_exhibit_graph_from_kg_projection_tables():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []
            self.rows = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            normalized = " ".join(query.split())
            self.calls.append((normalized, params))
            if "FROM kg_edges" in normalized:
                self.rows = [
                    {
                        "source": "exhibit:lever-play",
                        "target": "material:metal",
                        "label": "使用材料",
                        "type": "uses_material",
                    },
                    {
                        "source": "exhibit:lever-play",
                        "target": "exhibit:pulley-wall",
                        "label": "相似展项",
                        "type": "similar_to",
                    },
                ]
            elif "FROM kg_nodes" in normalized:
                self.rows = [
                    {"id": "exhibit:lever-play", "label": "杠杆乐园", "type": "exhibit"},
                    {"id": "material:metal", "label": "金属", "type": "material"},
                    {"id": "exhibit:pulley-wall", "label": "滑轮挑战墙", "type": "exhibit"},
                ]

        def fetchall(self):
            return self.rows

    class RecordingConnection:
        def __init__(self, cursor):
            self.cursor_instance = cursor

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_instance

    class RecordingPostgresRepository(PostgresExhibitRepository):
        def __init__(self):
            super().__init__("postgresql://example", initialize=False)
            self.cursor = RecordingCursor()

        def _connect(self):
            return RecordingConnection(self.cursor)

    repository = RecordingPostgresRepository()

    graph = repository.get_exhibit_graph("lever-play")

    assert [node.id for node in graph.nodes] == [
        "exhibit:lever-play",
        "material:metal",
        "exhibit:pulley-wall",
    ]
    assert [edge.type for edge in graph.edges] == ["uses_material", "similar_to"]
    assert any("FROM kg_edges" in query for query, _ in repository.cursor.calls)
    assert any("FROM kg_nodes" in query for query, _ in repository.cursor.calls)


def test_postgres_repository_reads_incoming_similarity_edges_for_exhibit_graph():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []
            self.rows = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            normalized = " ".join(query.split())
            self.calls.append((normalized, params))
            if "FROM kg_edges" in normalized:
                self.rows = (
                    [
                        {
                            "source": "exhibit:lever-play",
                            "target": "exhibit:pulley-wall",
                            "label": "similar exhibit",
                            "type": "similar_to",
                        }
                    ]
                    if params == ("exhibit:pulley-wall", "exhibit:pulley-wall", "exhibit:pulley-wall")
                    else []
                )
            elif "FROM kg_nodes" in normalized:
                self.rows = [
                    {"id": "exhibit:pulley-wall", "label": "Pulley Wall", "type": "exhibit"},
                    {"id": "exhibit:lever-play", "label": "Lever Play", "type": "exhibit"},
                ]

        def fetchall(self):
            return self.rows

    class RecordingConnection:
        def __init__(self, cursor):
            self.cursor_instance = cursor

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_instance

    class RecordingPostgresRepository(PostgresExhibitRepository):
        def __init__(self):
            super().__init__("postgresql://example", initialize=False)
            self.cursor = RecordingCursor()

        def _connect(self):
            return RecordingConnection(self.cursor)

    repository = RecordingPostgresRepository()

    graph = repository.get_exhibit_graph("pulley-wall")

    assert [node.id for node in graph.nodes] == ["exhibit:pulley-wall", "exhibit:lever-play"]
    assert [
        (edge.source, edge.type, edge.target)
        for edge in graph.edges
    ] == [("exhibit:lever-play", "similar_to", "exhibit:pulley-wall")]
    assert any(
        "target = %s" in query
        and params == ("exhibit:pulley-wall", "exhibit:pulley-wall", "exhibit:pulley-wall")
        for query, params in repository.cursor.calls
    )


def test_postgres_repository_reads_kg_snapshot_from_projection_tables():
    from app.repository import PostgresExhibitRepository, seed_exhibits

    class RecordingCursor:
        def __init__(self):
            self.calls = []
            self.rows = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            normalized = " ".join(query.split())
            self.calls.append((normalized, params))
            if "FROM kg_nodes" in normalized:
                self.rows = [
                    {
                        "id": "exhibit:lever-play",
                        "type": "exhibit",
                        "label": "杠杆乐园",
                        "attributes": {"category": "基础科学"},
                        "source_refs": ["exhibit:lever-play"],
                    },
                    {
                        "id": "material:metal",
                        "type": "material",
                        "label": "金属",
                        "attributes": {},
                        "source_refs": ["exhibit:lever-play"],
                    },
                ]
            elif "FROM kg_edges" in normalized:
                self.rows = [
                    {
                        "source": "exhibit:lever-play",
                        "target": "material:metal",
                        "type": "uses_material",
                        "label": "使用材料",
                        "weight": 1.0,
                        "source_refs": ["exhibit:lever-play"],
                    }
                ]

        def fetchall(self):
            return self.rows

    class RecordingConnection:
        def __init__(self, cursor):
            self.cursor_instance = cursor

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_instance

    class RecordingPostgresRepository(PostgresExhibitRepository):
        def __init__(self):
            super().__init__("postgresql://example", initialize=False)
            self.cursor = RecordingCursor()

        def _connect(self):
            return RecordingConnection(self.cursor)

        def list_exhibits(self, **_filters):
            return [seed_exhibits[0]]

    repository = RecordingPostgresRepository()

    snapshot = repository.get_kg_snapshot()

    assert [node.id for node in snapshot.nodes] == ["exhibit:lever-play", "material:metal"]
    assert snapshot.nodes[0].attributes == {"category": "基础科学"}
    assert snapshot.edges[0].source == "exhibit:lever-play"
    assert snapshot.edges[0].target == "material:metal"
    assert snapshot.adjacency == {"exhibit:lever-play": ["material:metal"]}
    assert any(evidence.source_id == "lever-play" for evidence in snapshot.evidences)


def test_postgres_repository_update_refreshes_record_and_search_embeddings():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return [{"payload": seed_exhibits[0].model_dump(mode="json")}]

    class RecordingConnection:
        def __init__(self, cursor):
            self.cursor_instance = cursor

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_instance

    class RecordingPostgresRepository(PostgresExhibitRepository):
        def __init__(self):
            super().__init__("postgresql://example", initialize=False)
            self.cursor = RecordingCursor()

        def get_exhibit(self, exhibit_id: str):
            return seed_exhibits[0] if exhibit_id == "lever-play" else None

        def _connect(self):
            return RecordingConnection(self.cursor)

    updated = seed_exhibits[0].model_copy(
        update={
            "description": "更新后的低龄儿童力学展项资料，用于刷新语义检索和 GraphRAG 引用。",
            "tags": ["更新后标签", "语义检索"],
        }
    )
    repository = RecordingPostgresRepository()

    result = repository.update_exhibit("lever-play", updated)

    assert result == updated
    update_calls = [call for call in repository.cursor.calls if "UPDATE exhibit_records" in call[0]]
    delete_calls = [call for call in repository.cursor.calls if "DELETE FROM search_embeddings" in call[0]]
    insert_calls = [call for call in repository.cursor.calls if "INSERT INTO search_embeddings" in call[0]]

    assert update_calls
    assert "embedding = %s::vector" in update_calls[0][0]
    assert delete_calls
    assert delete_calls[0][1] == ("exhibit", "lever-play")
    assert insert_calls
    assert insert_calls[0][1][0] == "exhibit:lever-play"
    assert any("DELETE FROM kg_edges" in query for query, _ in repository.cursor.calls)
    assert any("INSERT INTO kg_nodes" in query for query, _ in repository.cursor.calls)


def test_postgres_repository_delete_removes_search_embeddings():
    from app.repository import PostgresExhibitRepository

    class RecordingCursor:
        def __init__(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

        def fetchall(self):
            return []

    class RecordingConnection:
        def __init__(self, cursor):
            self.cursor_instance = cursor

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_instance

    class RecordingPostgresRepository(PostgresExhibitRepository):
        def __init__(self):
            super().__init__("postgresql://example", initialize=False)
            self.cursor = RecordingCursor()

        def get_exhibit(self, exhibit_id: str):
            return seed_exhibits[0] if exhibit_id == "lever-play" else None

        def _connect(self):
            return RecordingConnection(self.cursor)

    repository = RecordingPostgresRepository()

    assert repository.delete_exhibit("lever-play") is True

    soft_delete_calls = [call for call in repository.cursor.calls if "UPDATE exhibit_records" in call[0]]
    embedding_delete_calls = [
        call for call in repository.cursor.calls if "DELETE FROM search_embeddings" in call[0]
    ]

    assert soft_delete_calls
    assert embedding_delete_calls
    assert embedding_delete_calls[0][1] == ("exhibit", "lever-play")
    assert any("DELETE FROM kg_edges" in query for query, _ in repository.cursor.calls)
    assert not any("INSERT INTO kg_nodes" in query for query, _ in repository.cursor.calls)
