#!/bin/bash
set -euo pipefail

HTTPS_TERMINATES_HERE="${HTTPS_TERMINATES_HERE:-1}"
DISABLE_SSH_PASSWORD_AUTH="${DISABLE_SSH_PASSWORD_AUTH:-1}"

if [ "$DISABLE_SSH_PASSWORD_AUTH" = "1" ]; then
  HAS_SSH_KEY=0
  for keyfile in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
    if [ -s "$keyfile" ] && grep -Eq '^(ssh-|ecdsa-|sk-)' "$keyfile"; then
      HAS_SSH_KEY=1
    fi
  done
  if [ "$HAS_SSH_KEY" != "1" ]; then
    echo "Refusing to disable SSH passwords: install an authorized key first." >&2
    exit 1
  fi
fi

apt update
apt install -y python3 python3-venv python3-pip git ufw curl sqlite3 rsync fail2ban
ufw allow OpenSSH || true
ufw allow 80/tcp || true
if [ "$HTTPS_TERMINATES_HERE" = "1" ]; then
  ufw allow 443/tcp || true
fi
ufw --force delete allow 8000/tcp || true
ufw deny 8000/tcp
ufw --force enable || true

cat > /etc/fail2ban/jail.d/enrwine-sshd.local <<'EOF'
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban

if [ "$DISABLE_SSH_PASSWORD_AUTH" = "1" ]; then
  mkdir -p /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/00-enrwine-hardening.conf <<'EOF'
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
EOF
  sshd -t
  SSH_EFFECTIVE="$(sshd -T)"
  if ! grep -qx 'passwordauthentication no' <<< "$SSH_EFFECTIVE" || \
     ! grep -qx 'kbdinteractiveauthentication no' <<< "$SSH_EFFECTIVE"; then
    echo "SSH config overrides hardening; review sshd_config before reloading." >&2
    exit 1
  fi
  systemctl reload ssh || systemctl reload sshd
fi
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
mkdir -p /opt/enrwine/data/photos /opt/enrwine/backups
if [ ! -d /opt/enrwine/repo/.git ]; then
  rm -rf /opt/enrwine/repo
  git clone https://github.com/Slava34654/coupleee.git /opt/enrwine/repo
else
  git -C /opt/enrwine/repo pull
fi
python3 -m venv /opt/enrwine/venv
/opt/enrwine/venv/bin/pip install --upgrade pip
/opt/enrwine/venv/bin/pip install -r /opt/enrwine/repo/backend/requirements.txt
/opt/enrwine/venv/bin/pip install uvicorn
cat > /etc/systemd/system/enrwine.service <<'EOF'
[Unit]
Description=Enrwine backend
After=network.target
[Service]
WorkingDirectory=/opt/enrwine/repo
Environment=COUPLE_DB=/opt/enrwine/data/couple.db
Environment=PHOTO_DIR=/opt/enrwine/data/photos
Environment=PORT=8000
Environment=FORWARDED_ALLOW_IPS=127.0.0.1
EnvironmentFile=-/etc/enrwine.env
ExecStartPre=/opt/enrwine/venv/bin/alembic -c /opt/enrwine/repo/backend/alembic.ini upgrade head
ExecStart=/opt/enrwine/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-access-log
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now enrwine
install -m 0644 /opt/enrwine/repo/deploy/enrwine-backup.service /etc/systemd/system/
install -m 0644 /opt/enrwine/repo/deploy/enrwine-backup.timer /etc/systemd/system/
install -m 0644 /opt/enrwine/repo/deploy/enrwine-healthcheck.service /etc/systemd/system/
install -m 0644 /opt/enrwine/repo/deploy/enrwine-healthcheck.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now enrwine-backup.timer enrwine-healthcheck.timer
sleep 3
echo "---HEALTH---"
curl --fail --silent http://127.0.0.1:8000/health
echo
systemctl status enrwine --no-pager || true
echo "---BOT---"
curl -s http://127.0.0.1:8000/health/bot || true
echo
echo "---APK---"
curl -sI http://127.0.0.1:8000/Enrwine.apk | head -5 || true
