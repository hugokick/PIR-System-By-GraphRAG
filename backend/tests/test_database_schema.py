from pathlib import Path


schema_sql = Path(__file__).resolve().parents[1] / "sql" / "001_init.sql"


def test_postgres_schema_defines_graph_tables():
    sql = schema_sql.read_text(encoding="utf-8")

    for table_name in [
        "exhibits",
        "projects",
        "owners",
        "suppliers",
        "materials",
        "themes",
        "interactions",
        "media_assets",
        "documents",
        "exhibit_materials",
        "exhibit_interactions",
        "exhibit_relations",
        "exhibit_documents",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in sql


def test_postgres_schema_enables_pgvector_for_future_semantic_search():
    sql = schema_sql.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "embedding vector(1536)" in sql


def test_postgres_schema_defines_search_embedding_table_for_runtime_vector_recall():
    sql = schema_sql.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS search_embeddings" in sql
    assert "owner_type TEXT NOT NULL" in sql
    assert "chunk_id TEXT" in sql
    assert "embedding vector(1536) NOT NULL" in sql
    assert "idx_search_embeddings_embedding" in sql
