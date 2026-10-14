#!/usr/bin/env bash
set -euo pipefail

backup_root="${FLUXSG_BACKUP_DIR:-./backups}"
latest_backup="$(find "${backup_root}" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -1 || true)"
if [[ -z "${latest_backup}" || ! -f "${latest_backup}/postgres.dump" ]]; then
  printf 'No PostgreSQL backup found under %s\n' "${backup_root}" >&2
  exit 1
fi

drill_database="fluxsg_restore_drill"
cleanup() {
  docker compose exec -T postgres dropdb \
    --username "${POSTGRES_USER:-fluxsg}" \
    --if-exists \
    --force \
    "${drill_database}" >/dev/null
}
trap cleanup EXIT

shasum -a 256 -c "${latest_backup}/SHA256SUMS"
cleanup
docker compose exec -T postgres createdb \
  --username "${POSTGRES_USER:-fluxsg}" \
  "${drill_database}"
docker compose exec -T postgres pg_restore \
  --username "${POSTGRES_USER:-fluxsg}" \
  --dbname "${drill_database}" \
  --no-owner \
  < "${latest_backup}/postgres.dump"

table_count="$(docker compose exec -T postgres psql \
  --username "${POSTGRES_USER:-fluxsg}" \
  --dbname "${drill_database}" \
  --tuples-only \
  --no-align \
  --command "select count(*) from information_schema.tables where table_schema not in ('pg_catalog', 'information_schema');")"

if [[ "${table_count}" -lt 1 ]]; then
  printf 'Restore drill failed: no application tables were restored.\n' >&2
  exit 1
fi

printf 'Restore drill passed with %s application tables in the isolated drill database.\n' "${table_count}"
