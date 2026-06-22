"""PKCE (Proof Key for Code Exchange) utilities for OAuth 2.0.

This module implements RFC 7636 PKCE support for OAuth 2.0 authorization
code grants, providing secure code_verifier and code_challenge generation.
"""

import hashlib
import os
import secrets
import string
from base64 import urlsafe_b64encode


def generate_code_verifier(length: int = 128) -> str:
    """Generate a PKCE code verifier per RFC 7636.

    The code verifier is a high-entropy cryptographic random string using
    unreserved URL characters ([A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~").

    Args:
        length: Length of the code verifier (43-128 characters per RFC 7636).
                Default: 128 for maximum entropy.

    Returns:
        A random code verifier string.

    Raises:
        ValueError: If length is not in the valid range (43-128).
    """
    if not (43 <= length <= 128):
        raise ValueError("Code verifier length must be between 43 and 128 characters")

    # Use secrets.token_urlsafe for URL-safe random bytes
    # Each byte becomes ~1.33 characters, so we need to generate enough bytes
    num_bytes = (length * 3) // 4 + 1
    random_chars = secrets.token_urlsafe(num_bytes)[:length]

    return random_chars


def generate_code_challenge(code_verifier: str, method: str = "S256") -> str:
    """Generate a PKCE code challenge per RFC 7636.

    Args:
        code_verifier: The code verifier string from generate_code_verifier().
        method: The challenge method, either 'S256' (recommended) or 'plain'.
                Default: 'S256'.

    Returns:
        The code challenge string.

    Raises:
        ValueError: If the method is not 'S256' or 'plain'.
        ValueError: If the code verifier length is invalid.
    """
    if method not in ("S256", "plain"):
        raise ValueError("Method must be 'S256' or 'plain'")

    verifier_len = len(code_verifier)
    if not (43 <= verifier_len <= 128):
        raise ValueError(
            f"Code verifier must be between 43 and 128 characters, got {verifier_len}"
        )

    if method == "plain":
        return code_verifier

    # S256 method: BASE64URL(SHA256(code_verifier))
    # 1. SHA256 hash the verifier
    # 2. Base64url encode without padding
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    # Use url_safe_b64encode and strip padding
    challenge = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return challenge


def verify_code_challenge(
    code_verifier: str, code_challenge: str, method: str = "S256"
) -> bool:
    """Verify a PKCE code challenge against a verifier.

    Args:
        code_verifier: The original code verifier.
        code_challenge: The code challenge to verify against.
        method: The challenge method used ('S256' or 'plain').

    Returns:
        True if the challenge matches the verifier, False otherwise.
    """
    try:
        computed_challenge = generate_code_challenge(code_verifier, method)
        return secrets.compare_digest(computed_challenge, code_challenge)
    except (ValueError, TypeError):
        return False
