#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.cloud.yml}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-exhibit_atlas}"
POSTGRES_USER="${POSTGRES_USER:-exhibit_atlas}"
FILE_STORAGE_VOLUME="${FILE_STORAGE_VOLUME:-exhibit_atlas_file_storage}"
NEO4J_VOLUME="${NEO4J_VOLUME:-exhibit_atlas_neo4j_data}"

BACKUP_DIR="${1:-}"

if [[ -z "${BACKUP_DIR}" ]]; then
  echo "Usage: CONFIRM_RESTORE=YES $0 <backup-dir>" >&2
  exit 2
fi

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Refusing to restore without CONFIRM_RESTORE=YES" >&2
  exit 2
fi

for required in manifest.json postgres.dump file_storage.tar.gz neo4j_data.tar.gz checksums.sha256; do
  if [[ ! -f "${BACKUP_DIR}/${required}" ]]; then
    echo "Missing backup artifact: ${BACKUP_DIR}/${required}" >&2
    exit 2
  fi
done

BACKUP_DIR="$(cd "${BACKUP_DIR}" && pwd)"

(
  cd "${BACKUP_DIR}"
  sha256sum -c checksums.sha256
)

echo "Stopping application containers before restore"
docker compose -f "${COMPOSE_FILE}" stop frontend backend

echo "Restoring PostgreSQL database ${POSTGRES_DB}"
cat "${BACKUP_DIR}/postgres.dump" | docker compose -f "${COMPOSE_FILE}" exec -T "${POSTGRES_SERVICE}" \
  pg_restore --clean --if-exists --no-owner --no-privileges \
  -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "Restoring file storage volume ${FILE_STORAGE_VOLUME}"
docker run --rm \
  -v "${FILE_STORAGE_VOLUME}:/volume" \
  -v "${BACKUP_DIR}:/backup:ro" \
  alpine:3.20 \
  sh -c 'rm -rf /volume/* /volume/.[!.]* /volume/..?* 2>/dev/null || true; tar -xzf /backup/file_storage.tar.gz -C /volume'

echo "Restoring Neo4j demo volume ${NEO4J_VOLUME}"
docker compose -f "${COMPOSE_FILE}" stop neo4j
docker run --rm \
  -v "${NEO4J_VOLUME}:/volume" \
  -v "${BACKUP_DIR}:/backup:ro" \
  alpine:3.20 \
  sh -c 'rm -rf /volume/* /volume/.[!.]* /volume/..?* 2>/dev/null || true; tar -xzf /backup/neo4j_data.tar.gz -C /volume'

echo "Starting containers after restore"
docker compose -f "${COMPOSE_FILE}" up -d postgres neo4j backend frontend

echo "Restore complete from ${BACKUP_DIR}"
