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
PYTHON="${BACKUP_PYTHON:-/opt/enrwine/venv/bin/python}"
SERVICE_NAME="${SERVICE_NAME-enrwine}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING=""
mkdir -p "$BACKUP_ROOT"
exec 9>"$BACKUP_ROOT/.backup.lock"
flock -n 9 || { echo "Backup or restore is running" >&2; exit 1; }

usage() {
  echo "Usage: $0 <local-couple.db> | --s3 <YYYYmmddTHHMMSSZ>" >&2
  exit 2
}

[ "$#" -ge 1 ] || usage
if [ "$1" = "--s3" ]; then
  [ "$#" -eq 2 ] || usage
  STAGING="$(mktemp -d)"
  trap 'rm -rf "$STAGING"' EXIT
  "$PYTHON" "$SCRIPT_DIR/s3-backup.py" restore \
    --snapshot "$2" --destination "$STAGING"
  SOURCE_DB="$STAGING/couple.db"
  SOURCE_PHOTOS="$STAGING/photos"
else
  [ "$#" -eq 1 ] || usage
  SOURCE_DB="$1"
  SOURCE_PHOTOS=""
fi

test -f "$SOURCE_DB"
test "$(sqlite3 "$SOURCE_DB" 'PRAGMA integrity_check;')" = "ok"
if [ -n "$SOURCE_PHOTOS" ]; then
  command -v rsync >/dev/null
fi
mkdir -p "$BACKUP_ROOT" "$(dirname "$DB_PATH")" "$PHOTO_PATH"

if [ -n "$SERVICE_NAME" ]; then
  systemctl stop "$SERVICE_NAME"
fi
trap '[ -z "$STAGING" ] || rm -rf "$STAGING"' EXIT

PRE_RESTORE_DIR="$BACKUP_ROOT/pre-restore-$(date -u +%Y%m%dT%H%M%SZ)"
PRE_RESTORE="$PRE_RESTORE_DIR/couple.db"
if [ -f "$DB_PATH" ]; then
  mkdir -p "$PRE_RESTORE_DIR"
  ESCAPED_PRE_RESTORE=${PRE_RESTORE//\'/\'\'}
  sqlite3 "$DB_PATH" ".backup '$ESCAPED_PRE_RESTORE'"
fi
ESCAPED_SOURCE_DB=${SOURCE_DB//\'/\'\'}
sqlite3 "$DB_PATH" ".restore '$ESCAPED_SOURCE_DB'"

if [ -n "$SOURCE_PHOTOS" ]; then
  rsync -a --delete "$SOURCE_PHOTOS/" "$PHOTO_PATH/"
fi
test "$(sqlite3 "$DB_PATH" 'PRAGMA integrity_check;')" = "ok"
if [ -n "$SERVICE_NAME" ]; then
  systemctl start "$SERVICE_NAME"
fi
echo "Restore completed from: $SOURCE_DB"
