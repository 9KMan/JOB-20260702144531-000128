"""HMAC-SHA256 signature verification for incoming webhooks."""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

from src.core.config import settings


def sign_payload(secret: str, body: bytes, timestamp: Optional[int] = None) -> str:
    """Return ``sha256=<hex_digest>`` style signature."""
    ts = timestamp if timestamp is not None else int(time.time())
    body_with_ts = f"{ts}.".encode() + body
    digest = hmac.new(secret.encode(), body_with_ts, hashlib.sha256).hexdigest()
    return f"sha256={ts}.{digest}"


def verify_signature(secret: str, body: bytes, signature: str, tolerance: int = 300) -> bool:
    """Verify ``sha256=<ts>.<digest>`` against a body, with timestamp tolerance."""
    if not signature or not signature.startswith("sha256="):
        return False
    try:
        _, payload = signature.split("=", 1)
        ts_str, digest = payload.split(".", 1)
        ts = int(ts_str)
    except (ValueError, AttributeError):
        return False

    if abs(int(time.time()) - ts) > tolerance:
        return False

    expected = hmac.new(
        secret.encode(),
        f"{ts}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, digest)


def webhook_secret_for(source: str) -> str:
    """Per-source webhook secret.

    In production these come from a secret manager. For local dev we derive
    one from the global SECRET_KEY + source name so each integration gets
    a deterministic but distinct value.
    """
    base = settings.SECRET_KEY
    return hmac.new(base.encode(), source.encode(), hashlib.sha256).hexdigest()
