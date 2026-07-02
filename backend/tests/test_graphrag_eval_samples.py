import json
from pathlib import Path

from app.repository import seed_exhibits
from app.services.graphrag import search_graphrag_context


def test_graphrag_eval_cases_remain_stable():
    cases = json.loads(
        Path("backend/tests/fixtures/graphrag_eval_cases.json").read_text(encoding="utf-8")
    )

    for case in cases:
        response = search_graphrag_context(
            case["query"],
            seed_exhibits,
            top_k=case.get("top_k", 3),
        )
        returned_ids = [item.exhibit.id for item in response.items]
        assert returned_ids[: len(case["expected_top_ids"])] == case["expected_top_ids"], case["query"]
