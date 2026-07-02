from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_script(name: str) -> str:
    return (ROOT / "deploy" / name).read_text(encoding="utf-8")


def test_cloud_backup_script_captures_database_and_named_volumes():
    script = read_script("backup-cloud.sh")

    assert "set -euo pipefail" in script
    assert "docker compose -f" in script
    assert "pg_dump -Fc" in script
    assert "exhibit_atlas_file_storage" in script
    assert "exhibit_atlas_neo4j_data" in script
    assert "manifest.json" in script
    assert "sha256sum" in script


def test_cloud_restore_script_requires_explicit_confirmation_and_manifest():
    script = read_script("restore-cloud.sh")

    assert "set -euo pipefail" in script
    assert "CONFIRM_RESTORE" in script
    assert "manifest.json" in script
    assert "pg_restore --clean --if-exists" in script
    assert "docker compose -f" in script
    assert "exhibit_atlas_file_storage" in script
    assert "exhibit_atlas_neo4j_data" in script
    assert "docker run --rm" in script
