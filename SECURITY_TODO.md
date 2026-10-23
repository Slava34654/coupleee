# Security TODO

Следующие операции выполняет владелец вручную после проверки production-конфигурации:

- перевыпустить Firebase service account key;
- сменить `TELEGRAM_BOT_TOKEN`;
- сменить S3 access key и secret key;
- сменить TMDB API key или bearer token.

После ротации старые ключи нужно отозвать у провайдеров, обновить `/etc/enrwine.env` и перезапустить сервис. Значения секретов нельзя добавлять в Git или документацию.
