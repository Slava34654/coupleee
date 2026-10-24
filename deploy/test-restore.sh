#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT
DB="$TEMP_ROOT/live.db"
PHOTOS="$TEMP_ROOT/photos"
BACKUPS="$TEMP_ROOT/backups"
mkdir -p "$PHOTOS"
mkdir -p "$BACKUPS/20000101T000000Z"
touch -d '16 days ago' "$BACKUPS/20000101T000000Z"

sqlite3 "$DB" "CREATE TABLE marker(value TEXT NOT NULL); INSERT INTO marker VALUES('before');"
printf 'photo-data' > "$PHOTOS/photo.jpg"

ENV_FILE="$TEMP_ROOT/missing.env" \
COUPLE_DB="$DB" PHOTO_DIR="$PHOTOS" BACKUP_DIR="$BACKUPS" \
BACKUP_ENABLE_S3=0 bash "$SCRIPT_DIR/backup.sh"

SNAPSHOT_DB="$(find "$BACKUPS" -mindepth 2 -maxdepth 2 -name couple.db -print -quit)"
test -n "$SNAPSHOT_DB"
test ! -d "$BACKUPS/20000101T000000Z"
sqlite3 "$DB" "UPDATE marker SET value='after';"

ENV_FILE="$TEMP_ROOT/missing.env" \
COUPLE_DB="$DB" PHOTO_DIR="$PHOTOS" BACKUP_DIR="$BACKUPS" \
SERVICE_NAME="" bash "$SCRIPT_DIR/restore.sh" "$SNAPSHOT_DB"

test "$(sqlite3 "$DB" 'SELECT value FROM marker;')" = "before"
test "$(sqlite3 "$DB" 'PRAGMA integrity_check;')" = "ok"
printf 'not a database' > "$TEMP_ROOT/corrupt.db"
if ENV_FILE="$TEMP_ROOT/missing.env" \
  COUPLE_DB="$DB" PHOTO_DIR="$PHOTOS" BACKUP_DIR="$BACKUPS" \
  SERVICE_NAME="" bash "$SCRIPT_DIR/restore.sh" "$TEMP_ROOT/corrupt.db"; then
  echo "Corrupt snapshot was accepted" >&2
  exit 1
fi
test "$(sqlite3 "$DB" 'SELECT value FROM marker;')" = "before"
echo "Backup restore test passed"
