from app.repository import seed_exhibits


def test_sync_demo_seed_only_creates_missing_exhibits(monkeypatch):
    from scripts import sync_demo_seed

    existing = {seed_exhibits[0].id: seed_exhibits[0]}
    created = []

    class FakeRepository:
        def get_exhibit(self, exhibit_id):
            return existing.get(exhibit_id)

        def create_exhibit(self, exhibit):
            created.append(exhibit.id)
            existing[exhibit.id] = exhibit
            return exhibit

        def list_exhibits(self):
            return list(existing.values())

    monkeypatch.setattr(sync_demo_seed, "repository", FakeRepository())

    result = sync_demo_seed.sync_demo_seeds()

    assert seed_exhibits[0].id in result["existing"]
    assert seed_exhibits[1].id in result["created"]
    assert len(result["created"]) == len(seed_exhibits) - 1
    assert created == result["created"]
    assert result["total"] == len(seed_exhibits)
