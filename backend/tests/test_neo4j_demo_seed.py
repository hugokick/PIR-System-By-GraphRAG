from app.neo4j_demo.seed import build_demo_seed_script, build_demo_seed_statements
from app.repository import seed_exhibits


def test_build_demo_seed_statements_contains_expected_labels_and_relationships():
    statements = build_demo_seed_statements(seed_exhibits)
    script = "\n".join(statements)

    assert "MERGE (e:Exhibit" in script
    assert "MERGE (p:Project" in script
    assert "MERGE (o:Owner" in script
    assert "MERGE (s:Supplier" in script
    assert "MERGE (m:Material" in script
    assert "MERGE (t:Theme" in script
    assert "MERGE (i:Interaction" in script
    assert "MERGE (d:Document" in script
    assert "MATCH (source:Exhibit" in script
    assert "MERGE (source)-[:BELONGS_TO_PROJECT" in script
    assert "SIMILAR_TO" in script


def test_build_demo_seed_script_returns_browser_ready_cypher():
    script = build_demo_seed_script(seed_exhibits[:1])

    assert script.startswith("// Neo4j demo graph seed")
    assert "MERGE (e:Exhibit" in script
    assert "MATCH (source:Exhibit" in script
    assert script.endswith("\n")
