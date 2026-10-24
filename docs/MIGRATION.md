# Stage 1 Security Migration

## Deployment order

This release changes session storage, photo uploads, and the WebSocket handshake. Deploy the server and Flutter client as one coordinated release.

1. Stop the backend so no old process can write plaintext session tokens.
2. Copy `couple.db` and `photos/` to storage outside the checkout and verify the copies.
3. Set a random `PHOTO_URL_HMAC_SECRET` of at least 32 bytes in `/etc/enrwine.env`.
4. Keep `PHOTO_UPLOAD_TOKEN_LEGACY=1` while already installed clients are upgraded.
5. Keep `PHOTOS_PUBLIC_LEGACY=0`. Enable it only as a short emergency rollback for unsigned photo links.
6. Upgrade the database with `alembic -c backend/alembic.ini upgrade head` and start the new backend.
7. Publish the Flutter client that requests `/photos/upload-token` and authenticates WebSocket connections with the first message.
8. After the supported client population has upgraded, set `PHOTO_UPLOAD_TOKEN_LEGACY=0` and restart the backend.

Configure the reverse proxy with a request-body limit slightly above `PHOTO_MAX_BYTES` (for example, 6 MiB for the default 5 MiB file limit). The application streams file contents to temporary storage, but the proxy limit prevents oversized multipart bodies from reaching the ASGI parser.

## Token migrations

- `0009_user_token_hash` adds and backfills `users.token_hash`. Its downgrade is tested and preserves plaintext tokens.
- `0010_clear_plaintext_user_tokens` clears `users.token`. This data operation is intentionally irreversible because SHA-256 digests cannot recover raw tokens. Roll back this migration only by restoring the verified pre-deployment database backup.
- New registrations and logins return the raw token once to the client but persist only its SHA-256 digest.
- Existing unexpired client tokens remain valid because `0009` hashes them before `0010` clears the plaintext column.

Do not run an old backend binary after `0010`: it reads `users.token` and will reject every session.

## API compatibility

Existing query/body `user_id` fields remain accepted during the compatibility window. Identity always comes from `X-Auth-Token`; a mismatched `user_id` returns `403`.

New client code should treat `user_id` as response/display data and must not use it as proof of identity. Removal plan:

1. Keep the fields through the current `2.15.x` client line.
2. Record route usage without logging tokens or request bodies.
3. Remove required `user_id` claims only after at least 90 days with no supported old-client traffic.
4. Announce the minimum supported client version before deleting the fields.

The old WebSocket query parameters are not accepted because URLs are commonly logged. Clients must send this first message within `WS_AUTH_TIMEOUT_SECONDS`:

```json
{"type":"auth","token":"<session token>"}
```

## Photo compatibility

- `POST /photos/upload-token` issues a short-lived, single-use upload capability.
- `POST /photos` accepts `X-Photo-Upload-Token`. Header-only legacy upload remains available only while `PHOTO_UPLOAD_TOKEN_LEGACY=1`.
- Upload responses retain the stable `url` field and also return `signed_url` for temporary header-free rendering.
- `GET /photos/{name}` accepts a valid HMAC URL or an authenticated owner/current partner request.
- `PHOTOS_PUBLIC_LEGACY=1` makes unsigned managed photo URLs public and should normally remain disabled.

## Validation

After deployment, verify:

```bash
curl -fsS https://your-host/health/storage
curl -fsS https://your-host/app/version
sudo journalctl -u enrwine -n 100 --no-pager
```

Check aggregate database state without printing credentials: every active user should have a non-empty `token_hash`, and `users.token` should be empty.
