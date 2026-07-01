from app.graphrag.models import GraphRAGFilters
from app.graphrag.search import search_graph_rag
from app.repository import seed_exhibits


def test_graph_rag_search_applies_budget_filters():
    response = search_graph_rag(
        "力学",
        seed_exhibits,
        filters=GraphRAGFilters(theme="力学", budget_max=180000),
        top_k=5,
    )

    assert [item.exhibit.id for item in response.items] == ["pulley-wall"]
