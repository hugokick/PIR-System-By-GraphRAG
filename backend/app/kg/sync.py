from app.schemas import ExhibitResponse

from .builder import build_exhibit_kg_snapshot
from .models import KGSnapshot


def sync_snapshot_after_upsert(
    snapshot: KGSnapshot,
    exhibit: ExhibitResponse,
    exhibits_after_change: list[ExhibitResponse],
) -> KGSnapshot:
    _ = snapshot
    if not any(item.id == exhibit.id for item in exhibits_after_change):
        exhibits_after_change = [*exhibits_after_change, exhibit]
    return build_exhibit_kg_snapshot(exhibits_after_change)


def sync_snapshot_after_delete(
    snapshot: KGSnapshot,
    exhibit_id: str,
    exhibits_after_delete: list[ExhibitResponse],
) -> KGSnapshot:
    _ = snapshot
    filtered = [item for item in exhibits_after_delete if item.id != exhibit_id]
    return build_exhibit_kg_snapshot(filtered)
