import os
import secrets


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("COUPLE_DB", os.path.join(BASE_DIR, "couple.db"))
TOKEN_TTL_MS = 30 * 24 * 60 * 60 * 1000
LOGIN_WINDOW_MS = 15 * 60 * 1000
LOGIN_BLOCK_MS = 15 * 60 * 1000
LOGIN_EMAIL_LIMIT = 5
LOGIN_IP_LIMIT = 100

PHOTO_DIR = os.environ.get("PHOTO_DIR", os.path.join(BASE_DIR, "photos"))
PHOTO_MAX_BYTES = int(os.environ.get("PHOTO_MAX_BYTES", str(5 * 1024 * 1024)))
PHOTO_USER_QUOTA_BYTES = int(
    os.environ.get("PHOTO_USER_QUOTA_BYTES", str(250 * 1024 * 1024))
)
PHOTO_TOTAL_QUOTA_BYTES = int(
    os.environ.get("PHOTO_TOTAL_QUOTA_BYTES", str(5 * 1024 * 1024 * 1024))
)
PHOTO_DAILY_BYTES = int(os.environ.get("PHOTO_DAILY_BYTES", str(50 * 1024 * 1024)))
PHOTO_UPLOAD_TOKEN_TTL_MS = int(os.environ.get("PHOTO_UPLOAD_TOKEN_TTL_MS", "120000"))
PHOTO_UPLOAD_WINDOW_MS = int(os.environ.get("PHOTO_UPLOAD_WINDOW_MS", "3600000"))
PHOTO_UPLOAD_USER_LIMIT = int(os.environ.get("PHOTO_UPLOAD_USER_LIMIT", "20"))
PHOTO_UPLOAD_IP_LIMIT = int(os.environ.get("PHOTO_UPLOAD_IP_LIMIT", "20"))
PHOTO_UPLOAD_TOKEN_LEGACY = os.environ.get(
    "PHOTO_UPLOAD_TOKEN_LEGACY", "0"
).lower() in {"1", "true", "yes"}
PHOTOS_PUBLIC_LEGACY = os.environ.get("PHOTOS_PUBLIC_LEGACY", "1").lower() in {
    "1",
    "true",
    "yes",
}
PHOTO_URL_HMAC_SECRET = os.environ.get("PHOTO_URL_HMAC_SECRET", "").encode("utf-8")
EPHEMERAL_PHOTO_SECRET = secrets.token_bytes(32)

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "").strip()
S3_BUCKET = os.environ.get("S3_BUCKET", "").strip()
S3_REGION = os.environ.get("S3_REGION", "").strip() or "us-east-1"
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "").strip()
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "").strip()
S3_PHOTO_PREFIX = os.environ.get("S3_PHOTO_PREFIX", "photos/").strip("/") + "/"
S3_URL_TTL = int(os.environ.get("S3_URL_TTL", "3600"))

WS_AUTH_TIMEOUT_SECONDS = float(os.environ.get("WS_AUTH_TIMEOUT_SECONDS", "5"))
WS_IDLE_TIMEOUT_SECONDS = float(os.environ.get("WS_IDLE_TIMEOUT_SECONDS", "60"))
WS_MAX_MESSAGE_BYTES = int(os.environ.get("WS_MAX_MESSAGE_BYTES", "4096"))
