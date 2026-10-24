#!/bin/bash
set -euo pipefail
umask 077

ENV_FILE="${ENV_FILE:-/etc/enrwine.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

DB_PATH="${COUPLE_DB:-/opt/enrwine/data/couple.db}"
PHOTO_PATH="${PHOTO_DIR:-/opt/enrwine/data/photos}"
BACKUP_ROOT="${BACKUP_DIR:-/opt/enrwine/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
ENABLE_S3="${BACKUP_ENABLE_S3:-1}"
PYTHON="${BACKUP_PYTHON:-/opt/enrwine/venv/bin/python}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAPSHOT="$(date -u +%Y%m%dT%H%M%SZ)"
SNAPSHOT_DIR="$BACKUP_ROOT/$SNAPSHOT"
LOCK_FILE="$BACKUP_ROOT/.backup.lock"

command -v sqlite3 >/dev/null
test -f "$DB_PATH"
[[ "$RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || { echo "Invalid retention" >&2; exit 1; }
mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"
exec 9>"$LOCK_FILE"
flock -n 9 || { echo "Backup is already running" >&2; exit 1; }
mkdir "$SNAPSHOT_DIR"

TEMP_DB="$SNAPSHOT_DIR/couple.db.tmp"
FINAL_DB="$SNAPSHOT_DIR/couple.db"
trap 'rm -f "$TEMP_DB"' EXIT
ESCAPED_TEMP_DB=${TEMP_DB//\'/\'\'}
sqlite3 "$DB_PATH" ".backup '$ESCAPED_TEMP_DB'"
test "$(sqlite3 "$TEMP_DB" 'PRAGMA integrity_check;')" = "ok"
mv "$TEMP_DB" "$FINAL_DB"

if [ "$ENABLE_S3" = "1" ]; then
  "$PYTHON" "$SCRIPT_DIR/s3-backup.py" backup \
    --database "$FINAL_DB" \
    --photos "$PHOTO_PATH" \
    --snapshot "$SNAPSHOT" \
    --retention-days "$RETENTION_DAYS"
fi

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d \
  \( -name '[0-9]*T[0-9]*Z' -o -name 'pre-restore-*' \) \
  -mtime "+$((RETENTION_DAYS - 1))" -exec rm -rf -- {} +
echo "Backup completed: $SNAPSHOT"
