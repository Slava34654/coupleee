#!/bin/bash
# Применяет секреты Enrwine без ручного редактирования файлов.
# Секреты передаются переменными окружения (можно вставлять из браузера):
#   TELEGRAM_BOT_TOKEN='123456:ABC...' TELEGRAM_BOT_NAME='MyBot'
#   FIREBASE_SERVICE_ACCOUNT_BASE64='...'  (или FIREBASE_SERVICE_ACCOUNT_JSON='...')
#   S3_ENDPOINT='https://s3.example.com' S3_BUCKET='bucket' S3_REGION='region'
#   S3_ACCESS_KEY_ID='...' S3_SECRET_ACCESS_KEY='...'
#   TMDB_BEARER_TOKEN='...'
#   bash apply-secrets.sh
set -e
ENV=/etc/enrwine.env
touch "$ENV"; chmod 600 "$ENV"
set_var() {
  if [ -n "$2" ]; then
    grep -v "^$1=" "$ENV" > "$ENV.tmp" || true
    mv "$ENV.tmp" "$ENV"
    printf '%s=%s\n' "$1" "$2" >> "$ENV"
  fi
}
set_var TELEGRAM_BOT_TOKEN "$TELEGRAM_BOT_TOKEN"
set_var TELEGRAM_BOT_NAME "$TELEGRAM_BOT_NAME"
set_var FIREBASE_SERVICE_ACCOUNT_BASE64 "$FIREBASE_SERVICE_ACCOUNT_BASE64"
set_var FIREBASE_SERVICE_ACCOUNT_JSON "$FIREBASE_SERVICE_ACCOUNT_JSON"
set_var S3_ENDPOINT "$S3_ENDPOINT"
set_var S3_BUCKET "$S3_BUCKET"
set_var S3_REGION "$S3_REGION"
set_var S3_ACCESS_KEY_ID "$S3_ACCESS_KEY_ID"
set_var S3_SECRET_ACCESS_KEY "$S3_SECRET_ACCESS_KEY"
set_var S3_BACKUP_PREFIX "$S3_BACKUP_PREFIX"
set_var BACKUP_DIR "$BACKUP_DIR"
set_var BACKUP_RETENTION_DAYS "$BACKUP_RETENTION_DAYS"
set_var BACKUP_ENABLE_S3 "$BACKUP_ENABLE_S3"
set_var TMDB_API_KEY "$TMDB_API_KEY"
set_var TMDB_BEARER_TOKEN "$TMDB_BEARER_TOKEN"
mkdir -p /etc/systemd/system/enrwine.service.d
printf '[Service]\nEnvironmentFile=/etc/enrwine.env\n' > /etc/systemd/system/enrwine.service.d/secrets.conf
systemctl daemon-reload
systemctl restart enrwine
sleep 4
echo "---BOT---"
curl -s http://127.0.0.1:8000/health/bot || true
echo
echo "---STORAGE---"
curl -s http://127.0.0.1:8000/health/storage || true
echo
echo "---PUSH---"
curl -s http://127.0.0.1:8000/health/push || true
echo
echo "---HEALTH---"
curl -s http://127.0.0.1:8000/health || true
echo
