# Enrwine Production Deployment

Production использует systemd, reverse proxy и отдельный каталог данных. Секреты хранятся вне репозитория в `/etc/enrwine.env`.

## FirstVDS

Скрипт `deploy/firstvds-setup.sh`:

- устанавливает Python и системные зависимости;
- создаёт `/opt/enrwine/data/photos`;
- устанавливает `backend/requirements.txt` в `/opt/enrwine/venv`;
- запускает Alembic перед стартом Uvicorn;
- слушает только `127.0.0.1:8000` за reverse proxy.

Перед первым запуском проверьте URL репозитория внутри скрипта. Затем на сервере:

```bash
sudo bash deploy/firstvds-setup.sh
sudo systemctl status enrwine
```

Для обновления:

```bash
git -C /opt/enrwine/repo pull
/opt/enrwine/venv/bin/pip install -r /opt/enrwine/repo/backend/requirements.txt
sudo systemctl restart enrwine
```

## Секреты

Создайте `/etc/enrwine.env` с правами `600` или передайте значения окружением в `deploy/apply-secrets.sh`. Не размещайте значения в shell history, Git или документации.

```bash
sudo chmod 600 /etc/enrwine.env
sudo systemctl restart enrwine
```

Список поддерживаемых переменных находится в `.env.example`.

## Данные и backup

Production-данные находятся вне checkout:

- `/opt/enrwine/data/couple.db`
- `/opt/enrwine/data/photos/`

Перед миграцией создайте backup вне репозитория:

```bash
backup="/opt/enrwine/backup-$(date +%Y%m%d)"
sudo mkdir -p "$backup"
sudo cp /opt/enrwine/data/couple.db "$backup/"
sudo cp -a /opt/enrwine/data/photos "$backup/"
```

## Docker и Fly.io

`Dockerfile` устанавливает зависимости из `backend/requirements.txt`. Для Fly.io база и фотографии должны находиться на подключённом volume, пути задаются в `fly.toml`.

Бесплатный Render не поддерживается: без постоянного диска SQLite и фотографии теряются при перезапуске.
