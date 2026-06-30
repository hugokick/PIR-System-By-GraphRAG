from app.neo4j_demo.seed import build_demo_seed_script, build_demo_seed_statements
from app.neo4j_demo.demo_data import neo4j_demo_exhibits


def test_build_demo_seed_statements_contains_expected_labels_and_relationships():
    statements = build_demo_seed_statements(neo4j_demo_exhibits)
    script = "\n".join(statements)

    assert "MERGE (e:Exhibit" in script
    assert "MERGE (p:Project" in script
    assert "MERGE (o:Owner" in script
    assert "MERGE (s:Supplier" in script
    assert "MERGE (m:Material" in script
    assert "MERGE (t:Theme" in script
    assert "MERGE (i:Interaction" in script
    assert "MERGE (d:Document" in script
    assert "SIMILAR_TO" in script


def test_build_demo_seed_script_returns_browser_ready_cypher():
    script = build_demo_seed_script(neo4j_demo_exhibits[:1])

    assert script.startswith("// Neo4j demo graph seed")
    assert "MERGE (e:Exhibit" in script
    assert script.endswith("\n")


def test_neo4j_demo_exhibits_cover_four_frontend_demo_cases():
    exhibit_ids = {item.id for item in neo4j_demo_exhibits}
    exhibit_names = {item.name for item in neo4j_demo_exhibits}

    assert exhibit_ids == {"lever-play", "pulley-wall", "water-cycle", "space-dome"}
    assert exhibit_names == {"杠杆乐园", "滑轮挑战墙", "城市水循环沙盘", "星际穹幕影院"}


def test_build_demo_seed_script_contains_chinese_display_fields_for_space_dome():
    script = build_demo_seed_script(neo4j_demo_exhibits)

    assert "e.名称 = '星际穹幕影院'" in script
    assert "e.类别 = '宇宙探索'" in script
    assert "e.主题 = '天文'" in script
    assert "e.馆型 = '综合科技馆'" in script
    assert "e.供应商名称 = '星图数字'" in script
