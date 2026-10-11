#!/bin/bash
# Применяет секреты Enrwine без ручного редактирования файлов.
# Секреты передаются переменными окружения (можно вставлять из браузера):
#   TELEGRAM_BOT_TOKEN='123456:ABC...' TELEGRAM_BOT_NAME='MyBot'
#   FIREBASE_SERVICE_ACCOUNT_BASE64='...'  (или FIREBASE_SERVICE_ACCOUNT_JSON='...')
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
mkdir -p /etc/systemd/system/enrwine.service.d
printf '[Service]\nEnvironmentFile=/etc/enrwine.env\n' > /etc/systemd/system/enrwine.service.d/secrets.conf
systemctl daemon-reload
systemctl restart enrwine
sleep 4
echo "---BOT---"
curl -s http://127.0.0.1:8000/health/bot || true
echo
echo "---PUSH---"
curl -s http://127.0.0.1:8000/health/push || true
echo
