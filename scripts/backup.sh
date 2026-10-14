#!/usr/bin/env bash
set -euo pipefail

backup_root="${FLUXSG_BACKUP_DIR:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="${backup_root}/${timestamp}"
mkdir -p "${backup_dir}"

docker compose exec -T postgres pg_dump \
  --username "${POSTGRES_USER:-fluxsg}" \
  --dbname "${POSTGRES_DB:-fluxsg}" \
  --format custom \
  --no-owner \
  > "${backup_dir}/postgres.dump"

docker compose exec -T object-store tar -C /data -czf - . > "${backup_dir}/object-store.tar.gz"
shasum -a 256 "${backup_dir}/postgres.dump" "${backup_dir}/object-store.tar.gz" \
  > "${backup_dir}/SHA256SUMS"

printf 'FluxSG backup created at %s\n' "${backup_dir}"
