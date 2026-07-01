from app.repository import ExhibitRepository, seed_exhibits
from app.schemas import DocumentChunk


class FakePostgresRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url


def test_repository_factory_uses_memory_repository_without_database_url():
    from app.repository import create_repository_from_env

    repository = create_repository_from_env({})

    assert isinstance(repository, ExhibitRepository)


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
