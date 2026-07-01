from collections import Counter

from ..schemas import DashboardMetric, DashboardSummaryResponse, ExhibitResponse


def summarize_dashboard(items: list[ExhibitResponse]) -> DashboardSummaryResponse:
    budget_bands = {
        "20万以下": 0,
        "20-50万": 0,
        "50万以上": 0,
    }
    categories: Counter[str] = Counter()
    themes: Counter[str] = Counter()
    review_statuses: Counter[str] = Counter()
    budget_total = 0

    for item in items:
        categories[item.category] += 1
        themes[item.theme.name] += 1
        review_statuses[item.review_status] += 1
        average_budget = (item.budget_min + item.budget_max) / 2
        budget_total += average_budget
        if average_budget < 200000:
            budget_bands["20万以下"] += 1
        elif average_budget <= 500000:
            budget_bands["20-50万"] += 1
        else:
            budget_bands["50万以上"] += 1

    return DashboardSummaryResponse(
        total=len(items),
        landed=sum(1 for item in items if item.status == "已落地"),
        avg_budget=round_half_up(budget_total / max(len(items), 1) / 10000),
        pending_review=review_statuses["待审核"],
        rejected_review=review_statuses["已退回"],
        categories=counter_metrics(categories),
        budget_bands=[DashboardMetric(label=label, count=count) for label, count in budget_bands.items()],
        themes=counter_metrics(themes),
        review_statuses=counter_metrics(review_statuses),
    )


def counter_metrics(counter: Counter[str]) -> list[DashboardMetric]:
    return [
        DashboardMetric(label=label, count=count)
        for label, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def round_half_up(value: float) -> int:
    return int(value + 0.5)
