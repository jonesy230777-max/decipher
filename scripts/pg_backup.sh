#!/usr/bin/env bash
# S092: Nightly Postgres dump. Retained 14 days locally.
# Called by APScheduler (02:30 AEST) and can be run manually.
#
# Usage: ./scripts/pg_backup.sh [backup_dir]
#
# Requires: pg_dump, gzip accessible in PATH.
# Honours: DECIPHER_DB_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD from .env.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Source .env if it exists and no env vars are set yet
if [[ -f "$REPO_ROOT/.env" && -z "${POSTGRES_DB:-}" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

BACKUP_DIR="${1:-$REPO_ROOT/var/backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%d_%H%M%S")
FILENAME="decipher_${TIMESTAMP}.sql.gz"
DEST="$BACKUP_DIR/$FILENAME"

DB_PORT="${DECIPHER_DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-decipher}"
DB_USER="${POSTGRES_USER:-decipher}"

echo "[pg_backup] Dumping $DB_NAME@localhost:$DB_PORT → $DEST"

# pg_dump runs inside the Docker container (pg_dump is not required on the host).
# Falls back to host pg_dump if docker is not available.
if docker inspect decipher-db &>/dev/null 2>&1; then
  docker exec \
    -e "PGPASSWORD=${POSTGRES_PASSWORD:-}" \
    decipher-db \
    pg_dump \
      --username="$DB_USER" \
      --no-password \
      --format=plain \
      "$DB_NAME" \
  | gzip > "$DEST"
else
  PGPASSWORD="${POSTGRES_PASSWORD:-}" \
    pg_dump \
      --host=localhost \
      --port="$DB_PORT" \
      --username="$DB_USER" \
      --no-password \
      --format=plain \
      "$DB_NAME" \
    | gzip > "$DEST"
fi

SIZE=$(du -h "$DEST" | cut -f1)
echo "[pg_backup] Done: $DEST ($SIZE)"

# Prune backups older than 14 days
find "$BACKUP_DIR" -name "decipher_*.sql.gz" -mtime +14 -print -delete

echo "[pg_backup] Pruned backups older than 14 days. Remaining:"
ls -lh "$BACKUP_DIR"/decipher_*.sql.gz 2>/dev/null || echo "  (none)"
