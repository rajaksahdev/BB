"""Authentication: verify Supabase JWTs (and a dev fallback) -> User row.

Production: the frontend logs in via Supabase, which issues a JWT. New Supabase
projects sign tokens with asymmetric keys (ES256) — when ``SUPABASE_URL`` is
set we verify against the project's public JWKS. Older projects sign HS256 with
a shared secret (``SUPABASE_JWT_SECRET``). Either way we map ``sub`` (the
Supabase user UUID) to a local ``users`` row.

Local dev (no Supabase needed): when ``AUTH_DEV_MODE`` is on, a token of the
form ``dev:you@example.com`` authenticates as a deterministic test user. This
keeps Phase 3 fully testable before Supabase keys exist. Turn it OFF in prod.
"""

import uuid
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

settings = get_settings()

_DEV_PREFIX = "dev:"
_DEV_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "backtestlab.dev")


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    """Cached JWKS client for the Supabase project (keys cached in-process)."""
    base = settings.supabase_url.rstrip("/")
    return jwt.PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True)


def get_or_create_user(db: Session, user_id: uuid.UUID, email: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=email or f"{user_id}@unknown.local", tier="free")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")
    token = authorization[len("Bearer ") :].strip()

    # --- Dev fallback ---
    if settings.auth_dev_mode and token.startswith(_DEV_PREFIX):
        email = token[len(_DEV_PREFIX) :].strip().lower()
        if not email:
            raise HTTPException(status_code=401, detail="Dev token needs an email: 'dev:you@example.com'.")
        user_id = uuid.uuid5(_DEV_NAMESPACE, email)
        return get_or_create_user(db, user_id, email)

    # --- Supabase JWT ---
    if not (settings.supabase_url or settings.supabase_jwt_secret):
        raise HTTPException(
            status_code=503,
            detail=(
                "Auth not configured. Set SUPABASE_URL (JWKS) or "
                "SUPABASE_JWT_SECRET (or use a 'dev:' token in development)."
            ),
        )
    try:
        if settings.supabase_url:
            key = _jwks_client().get_signing_key_from_jwt(token).key
            algorithms = ["ES256", "RS256"]
        else:
            key = settings.supabase_jwt_secret
            algorithms = ["HS256"]
        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=settings.supabase_jwt_aud,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim.")
    return get_or_create_user(db, uuid.UUID(str(sub)), payload.get("email", ""))
