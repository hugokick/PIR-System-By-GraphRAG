from app.repository import ExhibitRepository, seed_exhibits


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


def test_postgres_repository_maps_json_payload_rows_to_exhibits():
    from app.repository import PostgresExhibitRepository

    repository = PostgresExhibitRepository("postgresql://example", initialize=False)
    row = {"payload": seed_exhibits[0].model_dump(mode="json")}

    exhibit = repository.exhibit_from_row(row)

    assert exhibit.id == "lever-play"
    assert exhibit.theme.name == "力学"
    assert exhibit.related_exhibit_ids == ["pulley-wall"]
