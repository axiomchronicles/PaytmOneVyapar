from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    AuthResult,
    LogoutRequest,
    OAuthExchangeRequest,
    OAuthStartResponse,
    OtpChallengeResponse,
    OtpRequest,
    OtpResendRequest,
    OtpVerifyRequest,
    RefreshRequest,
    RegistrationRequest,
    TokenResponse,
    UserMeResponse,
)
from app.application.services.auth_service import (
    OAuthService,
    OtpService,
    RegistrationService,
    SessionService,
    mask_phone,
)
from app.core.config import Settings, get_settings
from app.core.dependencies import Principal, get_current_principal
from app.core.errors import AuthenticationError, InvalidOtpError, InvalidRequestError, ProviderError
from app.core.security import verify_password
from app.domain.enums import OAuthProvider
from app.infrastructure.db.models import Merchant, Store, User
from app.infrastructure.db.repositories.merchants import MerchantRepository
from app.infrastructure.db.session import get_session

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def token(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await MerchantRepository(session).user_by_email(form.username.lower())
    if (
        user is None
        or not user.is_active
        or user.password_hash is None
        or not verify_password(form.password, user.password_hash)
    ):
        raise AuthenticationError("Invalid email or password")
    result = await SessionService(session, settings).issue(user, device_name=form.client_id)
    await session.commit()
    return TokenResponse.model_validate(result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    result = await SessionService(session, settings).refresh(
        body.refresh_token, device_name=body.device_name
    )
    await session.commit()
    return TokenResponse.model_validate(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    service = SessionService(session, settings)
    await service.revoke(principal.session_id)
    if body.refresh_token:
        await service.revoke_token(body.refresh_token)
    await session.commit()


def _request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _otp_service(request: Request, session: AsyncSession, settings: Settings) -> OtpService:
    return OtpService(session, settings, getattr(request.app.state, "otp_delivery", None))


@router.post("/otp/request", response_model=OtpChallengeResponse, status_code=201)
async def request_otp(
    body: OtpRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> OtpChallengeResponse:
    try:
        challenge, _ = await _otp_service(request, session, settings).request(
            body.identifier,
            purpose=body.purpose,
            request_ip=_request_ip(request),
        )
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc
    await session.commit()
    return OtpChallengeResponse(
        challenge_id=challenge.id,
        destination=mask_phone(challenge.identifier),
        expires_at=challenge.expires_at,
        resend_available_at=challenge.resend_available_at,
    )


@router.post("/otp/verify", response_model=AuthResult)
async def verify_otp(
    body: OtpVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResult:
    try:
        result = await _otp_service(request, session, settings).verify(
            body.challenge_id, body.otp, device_name=body.device_name
        )
    except InvalidOtpError:
        await session.commit()
        raise
    await session.commit()
    return AuthResult.model_validate(result)


@router.post("/otp/resend", response_model=OtpChallengeResponse)
async def resend_otp(
    body: OtpResendRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> OtpChallengeResponse:
    challenge = await _otp_service(request, session, settings).resend(body.challenge_id)
    await session.commit()
    return OtpChallengeResponse(
        challenge_id=challenge.id,
        destination=mask_phone(challenge.identifier),
        expires_at=challenge.expires_at,
        resend_available_at=challenge.resend_available_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegistrationRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    try:
        result = await RegistrationService(session, settings).register(**body.model_dump())
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        from app.core.errors import ConflictError

        raise ConflictError("An account already exists for these details") from exc
    return TokenResponse.model_validate(result)


def _oauth_provider(provider: str) -> OAuthProvider:
    try:
        return OAuthProvider(provider.upper())
    except ValueError as exc:
        raise InvalidRequestError("Unsupported OAuth provider") from exc


@router.post("/oauth/{provider}/start", response_model=OAuthStartResponse, status_code=201)
async def start_oauth(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> OAuthStartResponse:
    selected = _oauth_provider(provider)
    service = OAuthService(session, settings, request.app.state.oauth_verifier)
    challenge, state_value, nonce, client_id = await service.start(selected)
    await session.commit()
    return OAuthStartResponse(
        challenge_id=challenge.id,
        provider=selected,
        state=state_value,
        nonce=nonce,
        client_id=client_id,
        expires_at=challenge.expires_at,
    )


@router.post("/oauth/{provider}/exchange", response_model=AuthResult)
async def exchange_oauth(
    provider: str,
    body: OAuthExchangeRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResult:
    result = await OAuthService(session, settings, request.app.state.oauth_verifier).exchange(
        _oauth_provider(provider), **body.model_dump()
    )
    await session.commit()
    return AuthResult.model_validate(result)


@router.post("/oauth/{provider}/link")
async def link_oauth(
    provider: str,
    body: OAuthExchangeRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    result = await OAuthService(session, settings, request.app.state.oauth_verifier).exchange(
        _oauth_provider(provider),
        **body.model_dump(),
        link_user_id=principal.user_id,
    )
    await session.commit()
    return result


@router.get("/oauth/{provider}/authorize")
async def authorize_oauth(
    provider: str,
    request: Request,
    redirect_uri: str | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Any:
    selected = _oauth_provider(provider)
    service = OAuthService(session, settings, request.app.state.oauth_verifier)
    challenge, state_value, nonce, client_id = await service.start(selected)
    await session.commit()

    effective_redirect = (
        redirect_uri
        or settings.google_oauth_redirect_uri
        or "http://localhost:8000/api/v1/auth/oauth/google/callback"
    )
    state_payload = f"{challenge.id}:{state_value}:{nonce}"

    if selected == OAuthProvider.GOOGLE:
        query_params = {
            "client_id": client_id,
            "redirect_uri": effective_redirect,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state_payload,
            "nonce": nonce,
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(query_params)}"
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url=auth_url, status_code=307)
        return {"authorization_url": auth_url, "state": state_payload}

    raise InvalidRequestError(f"Direct authorize not implemented for {selected.value}")


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Any:
    selected = _oauth_provider(provider)
    if error:
        return {
            "status": "error",
            "provider": selected.value,
            "error": error,
            "error_description": error_description,
        }
    if not code:
        return {
            "status": "ready",
            "provider": selected.value,
            "message": f"{selected.value.title()} OAuth callback endpoint is active. Awaiting authorization code.",
        }

    # If state contains packed challenge_id:state_value:nonce, perform auto-exchange
    if state and ":" in state:
        try:
            parts = state.split(":", 2)
            if len(parts) == 3:
                challenge_id_str, state_val, nonce_val = parts
                service = OAuthService(session, settings, request.app.state.oauth_verifier)
                effective_redirect = (
                    settings.google_oauth_redirect_uri
                    or "http://localhost:8000/api/v1/auth/oauth/google/callback"
                )
                auth_result = await service.exchange(
                    selected,
                    challenge_id=UUID(challenge_id_str),
                    state=state_val,
                    nonce=nonce_val,
                    code=code,
                    redirect_uri=effective_redirect,
                )
                await session.commit()
                accept = request.headers.get("accept", "")
                if "text/html" in accept:
                    email_display = auth_result.get("email") or "Merchant"
                    html_content = f"""<!DOCTYPE html>
<html>
<head><title>Paytm ONE Vyapar - Sign-in Complete</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b1528; color: #ffffff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
.card {{ background: #13223f; border: 1px solid #1e3a6d; border-radius: 16px; padding: 40px; max-width: 480px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }}
h1 {{ color: #00b9f1; font-size: 24px; margin-bottom: 8px; }}
p {{ color: #94a3b8; font-size: 15px; line-height: 1.5; }}
.badge {{ background: #002970; color: #00b9f1; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; display: inline-block; margin: 16px 0; }}
</style>
</head>
<body>
<div class="card">
  <h1>Authentication Successful</h1>
  <div class="badge">Google Verified</div>
  <p>Welcome, <strong>{email_display}</strong>. Your account has been authenticated with Paytm ONE Vyapar.</p>
  <p>You may return to the application now.</p>
</div>
</body>
</html>"""
                    return HTMLResponse(content=html_content, status_code=200)
                return {
                    "status": "authenticated",
                    "provider": selected.value,
                    "result": auth_result,
                }
        except Exception as exc:
            logger.debug("oauth_auto_exchange_skipped", error=str(exc))

    return {
        "status": "success",
        "provider": selected.value,
        "code": code,
        "state": state,
        "message": "Authorization code received successfully. Submit to POST /api/v1/auth/oauth/{provider}/exchange to authenticate.",
    }


@router.post("/email/test")
async def test_email(
    to_email: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if not settings.resend_api_key:
        raise ProviderError("Resend API key is not configured")
    from app.integrations.email.resend import ResendEmailProvider

    provider = getattr(request.app.state, "email_provider", None)
    if provider is None:
        provider = ResendEmailProvider(
            api_key=settings.resend_api_key.get_secret_value(),
            from_email=settings.resend_from_email,
            client=getattr(request.app.state, "provider_http_client", None),
        )
    email_id = await provider.send_otp(to_email, otp="789012")
    return {"status": "sent", "provider": "resend", "email_id": email_id, "recipient": to_email}


@router.get("/me", response_model=UserMeResponse)
async def me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> UserMeResponse:
    user = await session.get(User, principal.user_id)
    if user is None:
        raise AuthenticationError("User not found")
    merchant = await session.get(Merchant, principal.merchant_id)
    business_name = merchant.name if merchant else "My Business"
    stores = list(await session.scalars(select(Store).where(Store.merchant_id == principal.merchant_id)))
    store_dicts = [
        {
            "id": str(s.id),
            "name": s.name,
            "address": s.address,
            "locality": (s.address or {}).get(
                "area_locality",
                (s.address or {}).get("locality", (s.address or {}).get("city", "Karol Bagh, New Delhi")),
            )
            if isinstance(s.address, dict)
            else "Karol Bagh, New Delhi",
        }
        for s in stores
    ]
    return UserMeResponse(
        user_id=user.id,
        merchant_id=user.merchant_id,
        role=user.role,
        account_type=user.role,
        email=user.email,
        business_name=business_name,
        phone_number=merchant.phone_number if merchant else None,
        gstin=merchant.gstin if merchant else None,
        pan=merchant.pan if merchant else None,
        is_email_verified=user.is_email_verified,
        is_phone_verified=user.is_phone_verified,
        stores=store_dicts,
    )
