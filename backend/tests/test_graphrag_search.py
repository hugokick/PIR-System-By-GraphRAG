from app.graphrag.models import GraphRAGFilters
from app.graphrag.search import search_graph_rag
from app.kg.models import KGEdge, KGNode, KGSnapshot
from app.repository import seed_exhibits


def test_graph_rag_search_applies_budget_filters():
    response = search_graph_rag(
        "力学",
        seed_exhibits,
        filters=GraphRAGFilters(theme="力学", budget_max=180000),
        top_k=5,
    )

    assert [item.exhibit.id for item in response.items] == ["pulley-wall"]


def test_graph_rag_search_includes_deduped_incoming_neighbor_edges():
    center_id = "exhibit:lever-play"
    related_id = "exhibit:incoming-related"
    snapshot = KGSnapshot(
        nodes=[
            KGNode(id=center_id, type="exhibit", label="Lever Play"),
            KGNode(id=related_id, type="exhibit", label="Incoming Related"),
        ],
        edges=[
            KGEdge(source=related_id, target=center_id, type="similar_to", label="similar exhibit"),
            KGEdge(source=related_id, target=center_id, type="similar_to", label="similar exhibit"),
        ],
        evidences=[],
        adjacency={related_id: [center_id]},
        warnings=[],
    )

    response = search_graph_rag(
        "lever-play",
        seed_exhibits,
        snapshot=snapshot,
        top_k=1,
    )

    assert response.items[0].exhibit.id == "lever-play"
    assert {node.id for node in response.items[0].neighborhood.nodes} == {center_id, related_id}
    assert [
        (edge.source, edge.type, edge.target)
        for edge in response.items[0].neighborhood.edges
    ] == [(related_id, "similar_to", center_id)]
