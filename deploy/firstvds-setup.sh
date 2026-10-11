#!/bin/bash
set -e
apt update
apt install -y python3 python3-venv python3-pip git ufw curl
ufw allow 22/tcp || true
ufw allow 80/tcp || true
ufw allow 8000/tcp || true
ufw --force enable || true
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
mkdir -p /opt/enrwine/data/photos
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
ExecStart=/opt/enrwine/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now enrwine
sleep 3
systemctl status enrwine --no-pager || true
echo "---BOT---"
curl -s http://127.0.0.1:8000/health/bot || true
echo
echo "---APK---"
curl -sI http://127.0.0.1:8000/Enrwine.apk | head -5 || true
