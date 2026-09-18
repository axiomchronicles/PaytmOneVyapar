from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError
from app.core.security import as_utc, utc_now
from app.infrastructure.db.models import RefreshSession, User
from app.infrastructure.db.session import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    merchant_id: UUID
    role: str
    session_id: UUID | None = None


async def get_current_principal(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Principal:
    try:
        claims = jwt.decode(
            token,
            settings.auth_jwt_secret.get_secret_value(),
            algorithms=[settings.auth_jwt_algorithm],
            options={"require": ["sub", "merchant_id", "exp", "iat"]},
        )
        if claims.get("type") != "access":
            raise AuthenticationError("Wrong token type")
        user_id = UUID(claims["sub"])
        merchant_id = UUID(claims["merchant_id"])
        session_id = UUID(claims["sid"]) if claims.get("sid") else None
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AuthenticationError("Invalid access token") from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active or user.merchant_id != merchant_id:
        raise AuthenticationError("User is inactive or no longer exists")
    if session_id is not None:
        refresh_session = await session.get(RefreshSession, session_id)
        if (
            refresh_session is None
            or refresh_session.revoked_at is not None
            or as_utc(refresh_session.expires_at) <= utc_now()
            or refresh_session.user_id != user.id
        ):
            raise AuthenticationError("Session is no longer active")
    return Principal(
        user_id=user.id,
        merchant_id=user.merchant_id,
        role=user.role,
        session_id=session_id,
    )
