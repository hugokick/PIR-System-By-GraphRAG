#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.cloud.yml}"
BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-exhibit_atlas}"
POSTGRES_USER="${POSTGRES_USER:-exhibit_atlas}"
FILE_STORAGE_VOLUME="${FILE_STORAGE_VOLUME:-exhibit_atlas_file_storage}"
NEO4J_VOLUME="${NEO4J_VOLUME:-exhibit_atlas_neo4j_data}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_ROOT_ABS="$(mkdir -p "${BACKUP_ROOT}" && cd "${BACKUP_ROOT}" && pwd)"
BACKUP_DIR="${BACKUP_ROOT_ABS}/pir-system-${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"

echo "Creating backup in ${BACKUP_DIR}"

docker compose -f "${COMPOSE_FILE}" exec -T "${POSTGRES_SERVICE}" \
  pg_dump -Fc -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  > "${BACKUP_DIR}/postgres.dump"

docker run --rm \
  -v "${FILE_STORAGE_VOLUME}:/volume:ro" \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.20 \
  tar -czf /backup/file_storage.tar.gz -C /volume .

docker run --rm \
  -v "${NEO4J_VOLUME}:/volume:ro" \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.20 \
  tar -czf /backup/neo4j_data.tar.gz -C /volume .

(
  cd "${BACKUP_DIR}"
  sha256sum postgres.dump file_storage.tar.gz neo4j_data.tar.gz > checksums.sha256
)

cat > "${BACKUP_DIR}/manifest.json" <<EOF
{
  "name": "PIR System cloud backup",
  "created_at": "${TIMESTAMP}",
  "compose_file": "${COMPOSE_FILE}",
  "postgres_service": "${POSTGRES_SERVICE}",
  "postgres_db": "${POSTGRES_DB}",
  "file_storage_volume": "${FILE_STORAGE_VOLUME}",
  "neo4j_volume": "${NEO4J_VOLUME}",
  "artifacts": [
    "postgres.dump",
    "file_storage.tar.gz",
    "neo4j_data.tar.gz",
    "checksums.sha256"
  ]
}
EOF

echo "Backup complete: ${BACKUP_DIR}"
