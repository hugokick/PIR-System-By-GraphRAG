import json

from app.main import repository
from app.repository import seed_exhibits


def sync_demo_seeds() -> dict[str, object]:
    created: list[str] = []
    existing: list[str] = []

    for exhibit in seed_exhibits:
        if repository.get_exhibit(exhibit.id) is None:
            repository.create_exhibit(exhibit)
            created.append(exhibit.id)
        else:
            existing.append(exhibit.id)

    return {
        "created": created,
        "existing": existing,
        "total": len(repository.list_exhibits()),
    }


if __name__ == "__main__":
    print(json.dumps(sync_demo_seeds(), ensure_ascii=False))
