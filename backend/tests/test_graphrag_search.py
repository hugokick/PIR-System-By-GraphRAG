from app.graphrag.models import GraphRAGFilters
from app.graphrag.search import search_graph_rag
from app.kg.models import KGEdge, KGNode, KGSnapshot
from app.repository import seed_exhibits
from app.schemas import DocumentAsset, DocumentChunk


def test_graph_rag_search_applies_budget_filters():
    response = search_graph_rag(
        "力学",
        seed_exhibits,
        filters=GraphRAGFilters(theme="力学", budget_max=180000),
        top_k=5,
    )

    assert [item.exhibit.id for item in response.items] == ["pulley-wall"]


def test_graph_rag_search_uses_query_understanding_for_chinese_business_intent():
    response = search_graph_rag(
        "找几个适合低龄儿童、预算不高、互动性强的力学展项",
        seed_exhibits,
        top_k=5,
    )

    assert response.total >= 2
    assert response.items[0].exhibit.id == "pulley-wall"
    joined_reasons = "；".join(response.items[0].reasons)
    assert "查询理解：主题 力学" in joined_reasons
    assert "查询理解：预算倾向 low" in joined_reasons
    assert "查询理解：人群 low_age_children" in joined_reasons


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


def test_graph_rag_search_cites_only_matched_documents_when_chunk_matches():
    first_document = DocumentAsset(
        id="first-doc",
        name="first-guide.txt",
        file_type="txt",
        url="/api/files/first-doc",
        source_note="unmatched source",
        chunks=[
            DocumentChunk(
                id="first-doc:chunk-1",
                text="first-only-token should not be cited for this query",
                sequence=1,
            )
        ],
    )
    second_document = DocumentAsset(
        id="second-doc",
        name="second-guide.txt",
        file_type="txt",
        url="/api/files/second-doc",
        source_note="matched source",
        chunks=[
            DocumentChunk(
                id="second-doc:chunk-1",
                text="second-only-token is the precise supporting evidence",
                sequence=1,
            )
        ],
    )
    target = seed_exhibits[0].model_copy(
        update={
            "documents": [first_document, second_document],
        }
    )

    response = search_graph_rag("second-only-token", [target], top_k=1)

    citation_ids = {citation.source_id for citation in response.items[0].citations}
    assert "second-doc" in citation_ids
    assert "first-doc" not in citation_ids
