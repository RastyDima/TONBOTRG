"""Telegram Mini App initData validation."""
import hashlib
import hmac
import json
import time
import urllib.parse

from config import BOT_TOKEN

TELEGRAM_AUTH_TTL = 86400  # 24 hours


def validate_telegram_init_data(init_data: str) -> dict | None:
    """Validate Telegram WebApp initData.

    Returns parsed user dict on success, None on failure.
    """
    if not init_data:
        return None

    parsed = dict(urllib.parse.parse_qsl(init_data))
    if "hash" not in parsed:
        return None

    received_hash = parsed.pop("hash")
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(
        b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > TELEGRAM_AUTH_TTL:
        return None

    try:
        user = json.loads(parsed.get("user", "{}"))
    except (json.JSONDecodeError, TypeError):
        return None

    if not user.get("id"):
        return None

    return user
