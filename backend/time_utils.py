import datetime
import time


UTC = datetime.timezone.utc


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(UTC)


def utc_today() -> datetime.date:
    return utc_now().date()


def utc_iso() -> str:
    return utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def unix_ms() -> int:
    return time.time_ns() // 1_000_000


def parse_utc(value: str) -> datetime.datetime:
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
