import hashlib
import secrets
from contextvars import ContextVar

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


request_token: ContextVar[str] = ContextVar("request_token", default="")
request_user: ContextVar[object | None] = ContextVar("request_user", default=None)


class AuthTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token_context = request_token.set(request.headers.get("x-auth-token", ""))
        user_context = request_user.set(None)
        try:
            response = await call_next(request)
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault(
                "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
            )
            response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
            content_type = response.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                response.headers.setdefault("Cache-Control", "no-store")
                response.headers.setdefault(
                    "Content-Security-Policy",
                    "default-src 'none'; frame-ancestors 'none'",
                )
            forwarded_proto = request.headers.get("x-forwarded-proto", "")
            scheme = forwarded_proto.split(",", 1)[0].strip() or request.url.scheme
            if scheme.lower() == "https":
                response.headers.setdefault(
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains",
                )
            return response
        finally:
            request_user.reset(user_context)
            request_token.reset(token_context)


def new_token() -> str:
    return secrets.token_hex(16)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    if not 6 <= len(password) <= 128:
        raise HTTPException(400, "password must contain 6 to 128 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32
    )
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored.split("$", 2)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=16384,
            r=8,
            p=1,
            dklen=32,
        )
        return secrets.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


DUMMY_PASSWORD_HASH = (
    "scrypt$"
    + "00" * 16
    + "$"
    + hashlib.scrypt(
        b"invalid-login", salt=b"\0" * 16, n=16384, r=8, p=1, dklen=32
    ).hex()
)
