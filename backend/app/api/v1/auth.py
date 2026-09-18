from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import TokenResponse
from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError
from app.core.security import create_access_token, verify_password
from app.infrastructure.db.repositories.merchants import MerchantRepository
from app.infrastructure.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def token(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await MerchantRepository(session).user_by_email(form.username.lower())
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    access_token = create_access_token(
        subject=user.id,
        merchant_id=user.merchant_id,
        secret=settings.auth_jwt_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
        ttl_minutes=settings.auth_access_token_minutes,
    )
    return TokenResponse(access_token=access_token)
