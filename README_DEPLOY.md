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

`firstvds-setup.sh` оставляет приложение на `127.0.0.1:8000`, закрывает внешний
порт 8000, включает UFW, fail2ban и SSH-доступ только по ключам. Перед запуском
обязательно добавьте публичный ключ в `authorized_keys`. Если TLS завершается на
другом сервере, запускайте с `HTTPS_TERMINATES_HERE=0`; иначе открывается 443.

Для security-релиза сначала выполните порядок из `docs/MIGRATION.md`; обычный rolling restart небезопасен при очистке plaintext session tokens.

## Секреты

Создайте `/etc/enrwine.env` с правами `600` или передайте значения окружением в `deploy/apply-secrets.sh`. Не размещайте значения в shell history, Git или документации.

```bash
sudo chmod 600 /etc/enrwine.env
sudo systemctl restart enrwine
```

Список поддерживаемых переменных находится в `.env.example`.

Для S3-бэкапов задайте `S3_*`, `S3_BACKUP_PREFIX` и
`BACKUP_ENABLE_S3=1`. Не используйте основной `S3_PHOTO_PREFIX` как backup
prefix. Проверка конфигурации:

```bash
sudo systemctl start enrwine-backup.service
sudo systemctl status enrwine-backup.service
sudo systemctl list-timers 'enrwine-*'
```

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

Ежедневный `enrwine-backup.timer` создаёт SQLite snapshot через `.backup`,
проверяет его целостность, копирует БД и фотографии в timestamped S3 snapshot и
удаляет local/S3 snapshots старше 14 дней. Ручной backup и тест восстановления:

```bash
sudo systemctl start enrwine-backup.service
bash deploy/test-restore.sh
```

Восстановление выполняется только в окно обслуживания:

```bash
sudo bash deploy/restore.sh /opt/enrwine/backups/<timestamp>/couple.db
sudo bash deploy/restore.sh --s3 <timestamp>
```

Restore останавливает `enrwine`, проверяет snapshot, создаёт pre-restore копию и
запускает сервис после проверки новой БД. При ошибке восстановления сервис
остаётся остановленным для ручной проверки. Локальный restore восстанавливает
только БД; `--s3` восстанавливает БД и фото. Snapshot помечается завершённым только
после загрузки всех файлов, checksum БД проверяется при скачивании.

S3 backup включает фото из основного S3-префикса, даже если их нет локально.
Учётной записи backup нужны права на list/get/put/copy/delete и получение
versioning configuration бакета. В versioned bucket также нужны list/delete
object versions: retention удаляет старые версии и delete markers. Object Lock
или запрет удаления должны сигнализировать ошибкой backup, а не скрываться.
Используйте закрытый бакет и шифрование на стороне S3-провайдера.

SQLite snapshot консистентен, но фото копируются последовательно: общей
транзакции SQLite/S3 нет. Для строго согласованного disaster-recovery snapshot
создавайте копию в окно без записи/удаления фото. После восстановления старой
БД повторите обработку запросов удаления аккаунтов перед открытием трафика.

## Monitoring

`GET /health` возвращает `200` только при доступной SQLite БД, иначе `503`.
Локальный `enrwine-healthcheck.timer` проверяет endpoint каждую минуту; ошибки
видны через `journalctl -u enrwine-healthcheck.service`. Для контроля падения
всего сервера настройте внешний uptime-monitor на:

```text
https://153-76-163-41.sslip.io/health
```

Рекомендуемый интервал — 1 минута, ожидание — 10 секунд, оповещение после трёх
последовательных ошибок.

Для upload endpoint задайте на reverse proxy body limit немного выше `PHOTO_MAX_BYTES` (6 MiB при стандартном лимите 5 MiB).
Для nginx подключите содержимое `deploy/nginx-security.conf` внутри HTTPS `server`-блока. Оно включает HSTS, `nosniff`, body limit и отключает access log с URL capability-параметрами.

## Docker и Fly.io

`Dockerfile` устанавливает зависимости из `backend/requirements.txt`. Для Fly.io база и фотографии должны находиться на подключённом volume, пути задаются в `fly.toml`.

Бесплатный Render не поддерживается: без постоянного диска SQLite и фотографии теряются при перезапуске.
