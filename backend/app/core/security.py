from __future__ import annotations

from typing import Optional

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Simple in-memory JWKS cache (refreshed when key is not found)
_jwks_cache: dict = {}


async def _fetch_jwks() -> dict:
    """Download the Clerk JWKS and cache it."""
    global _jwks_cache
    url = settings.clerk_jwks_url
    if not url:
        raise AuthenticationError("Clerk JWKS URL is not configured.")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _get_rsa_key(token: str, jwks: dict) -> Optional[dict]:
    """Find the RSA key from JWKS that matches the token's `kid` header."""
    try:
        headers = jwt.get_unverified_header(token)
    except JWTError:
        return None

    kid = headers.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key.get("use"),
                "n": key["n"],
                "e": key["e"],
            }
    return None


async def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk-issued JWT and return its claims.

    Raises AuthenticationError on any failure.
    """
    global _jwks_cache

    if not _jwks_cache:
        await _fetch_jwks()

    rsa_key = _get_rsa_key(token, _jwks_cache)

    # Key not found — maybe JWKS has rotated; refresh once
    if rsa_key is None:
        await _fetch_jwks()
        rsa_key = _get_rsa_key(token, _jwks_cache)

    if rsa_key is None:
        raise AuthenticationError("Unable to find matching public key.")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except ExpiredSignatureError:
        raise AuthenticationError("Token has expired.")
    except JWTError as exc:
        logger.debug("JWT verification failed: %s", exc)
        raise AuthenticationError("Invalid token.")


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency — returns the Clerk user ID (``sub`` claim) from the
    Bearer token in the Authorization header.
    """
    if credentials is None:
        raise AuthenticationError("No authorization token provided.")

    payload = await verify_clerk_token(credentials.credentials)
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token is missing subject claim.")
    return user_id


async def get_current_user(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(lambda: None),  # replaced below with real dep
):
    """
    Resolve a Clerk user ID to the local User DB record.

    Import and use ``get_current_user_from_db`` in routes instead; this
    stub exists so the import graph stays clean.
    """
    raise NotImplementedError("Use get_current_user_from_db from app.api.deps")


# ── Full dependency (used in route files) ────────────────────────────────────

async def get_current_user_from_db(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(lambda: (_ for _ in ()).throw(RuntimeError("inject db"))),
):
    """Placeholder — real implementation wired in app.api.deps."""
    raise NotImplementedError


def require_auth(request: Request) -> str:
    """
    Synchronous helper for rate-limiter key functions; returns the clerk user
    id if already resolved, otherwise the client IP.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        # Don't verify again — just use it as a key string
        return auth_header[7:60]  # truncate for key safety
    return request.client.host if request.client else "anonymous"
