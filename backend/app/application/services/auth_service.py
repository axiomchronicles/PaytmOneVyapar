import hmac
import re
import secrets
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID

import httpx
import jwt
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    AuthenticationError,
    ConflictError,
    InvalidOtpError,
    OAuthCredentialError,
    OtpDeliveryUnavailableError,
    ProviderError,
    RateLimitError,
)
from app.core.security import (
    as_utc,
    create_access_token,
    create_registration_token,
    hash_password,
    token_digest,
    utc_now,
    verify_password,
)
from app.domain.enums import OAuthProvider, OtpPurpose
from app.infrastructure.db.models import (
    Merchant,
    OAuthChallenge,
    OAuthIdentity,
    OtpChallenge,
    RefreshSession,
    Store,
    User,
)


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        digits = f"91{digits}"
    if not 10 <= len(digits) <= 15:
        raise ValueError("Enter a valid phone number")
    return digits


def normalize_identifier(value: str) -> str:
    val = value.strip()
    if "@" in val:
        email = val.lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Enter a valid email address")
        return email
    return normalize_phone(val)


def mask_phone(value: str) -> str:
    if "@" in value:
        parts = value.split("@", 1)
        name, domain = parts[0], parts[1]
        masked = name[:2] + "•••" if len(name) > 2 else name[:1] + "•••"
        return f"{masked}@{domain}"
    return f"••••••{value[-4:]}"


def mask_identifier(value: str) -> str:
    return mask_phone(value)


class OtpDelivery(Protocol):
    async def send(self, identifier: str, otp: str, *, idempotency_key: str) -> None: ...


class WhatsAppOtpDelivery:
    def __init__(self, send_text: Callable[..., Awaitable[str]]) -> None:
        self._send_text = send_text

    async def send(self, identifier: str, otp: str, *, idempotency_key: str) -> None:
        await self._send_text(
            identifier,
            f"Your Paytm ONE Vyapar verification code is {otp}. It expires shortly. Do not share it.",
            idempotency_key=idempotency_key,
        )


class EmailOtpDelivery:
    def __init__(self, send_otp: Callable[..., Awaitable[str]]) -> None:
        self._send_otp = send_otp

    async def send(self, identifier: str, otp: str, *, idempotency_key: str) -> None:
        await self._send_otp(identifier, otp, idempotency_key=idempotency_key)


class MultiChannelOtpDelivery:
    def __init__(
        self,
        *,
        whatsapp: OtpDelivery | None = None,
        email: OtpDelivery | None = None,
    ) -> None:
        self.whatsapp = whatsapp
        self.email = email

    async def send(self, identifier: str, otp: str, *, idempotency_key: str) -> None:
        if "@" in identifier:
            if self.email is not None:
                await self.email.send(identifier, otp, idempotency_key=idempotency_key)
                return
            raise OtpDeliveryUnavailableError("Email OTP delivery is not configured")
        if self.whatsapp is not None:
            await self.whatsapp.send(identifier, otp, idempotency_key=idempotency_key)
            return
        if self.email is not None:
            # Fallback for phone when email configured and identifier looks like email
            raise OtpDeliveryUnavailableError("WhatsApp OTP delivery is not configured")
        raise OtpDeliveryUnavailableError("OTP delivery is temporarily unavailable")


class SessionService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def issue(self, user: User, *, device_name: str | None = None) -> dict[str, Any]:
        refresh_token = secrets.token_urlsafe(48)
        row = RefreshSession(
            user_id=user.id,
            merchant_id=user.merchant_id,
            token_hash=token_digest(refresh_token),
            expires_at=utc_now() + timedelta(days=self.settings.auth_refresh_token_days),
            device_name=device_name,
        )
        self.session.add(row)
        await self.session.flush()
        access_token = create_access_token(
            subject=user.id,
            merchant_id=user.merchant_id,
            session_id=row.id,
            secret=self.settings.auth_jwt_secret.get_secret_value(),
            algorithm=self.settings.auth_jwt_algorithm,
            ttl_minutes=self.settings.auth_access_token_minutes,
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.settings.auth_access_token_minutes * 60,
        }

    async def refresh(self, refresh_token: str, *, device_name: str | None = None) -> dict[str, Any]:
        row = await self.session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_digest(refresh_token))
            .with_for_update()
        )
        if row is None or row.revoked_at is not None or as_utc(row.expires_at) <= utc_now():
            raise AuthenticationError("Refresh session is invalid or expired")
        user = await self.session.get(User, row.user_id)
        if user is None or not user.is_active or user.merchant_id != row.merchant_id:
            raise AuthenticationError("Refresh session is no longer valid")
        row.revoked_at = utc_now()
        result = await self.issue(user, device_name=device_name or row.device_name)
        replacement = await self.session.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == token_digest(result["refresh_token"])
            )
        )
        row.replaced_by_id = replacement.id if replacement else None
        return result

    async def revoke(self, session_id: UUID | None) -> None:
        if session_id is None:
            return
        row = await self.session.scalar(
            select(RefreshSession).where(RefreshSession.id == session_id).with_for_update()
        )
        if row is not None and row.revoked_at is None:
            row.revoked_at = utc_now()

    async def revoke_token(self, refresh_token: str) -> None:
        row = await self.session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_digest(refresh_token))
            .with_for_update()
        )
        if row is not None and row.revoked_at is None:
            row.revoked_at = utc_now()


class OtpService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        delivery: OtpDelivery | None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.delivery = delivery

    async def request(
        self,
        identifier: str,
        *,
        purpose: OtpPurpose,
        request_ip: str,
    ) -> tuple[OtpChallenge, bool]:
        normalized = normalize_identifier(identifier)
        identifier_hash = token_digest(normalized)
        ip_hash = token_digest(f"{request_ip}:{self.settings.auth_otp_secret.get_secret_value()}")
        window = utc_now() - timedelta(hours=1)
        identifier_count = await self.session.scalar(
            select(func.count(OtpChallenge.id)).where(
                OtpChallenge.identifier_hash == identifier_hash,
                OtpChallenge.created_at >= window,
            )
        )
        ip_count = await self.session.scalar(
            select(func.count(OtpChallenge.id)).where(
                OtpChallenge.request_ip_hash == ip_hash,
                OtpChallenge.created_at >= window,
            )
        )
        if (identifier_count or 0) >= 5 or (ip_count or 0) >= 20:
            raise RateLimitError("Please wait before requesting another code")

        should_deliver = True
        if self.delivery is None:
            raise OtpDeliveryUnavailableError("OTP delivery is temporarily unavailable")

        otp = f"{secrets.randbelow(1_000_000):06d}"
        now = utc_now()
        challenge = OtpChallenge(
            identifier=normalized,
            identifier_hash=identifier_hash,
            purpose=purpose,
            otp_hash=hash_password(otp),
            request_ip_hash=ip_hash,
            expires_at=now + timedelta(minutes=self.settings.auth_otp_expiry_minutes),
            resend_available_at=now + timedelta(seconds=self.settings.auth_otp_resend_seconds),
            max_attempts=self.settings.auth_otp_max_attempts,
            max_resends=self.settings.auth_otp_max_resends,
        )
        self.session.add(challenge)
        await self.session.flush()
        if should_deliver and self.delivery is not None:
            await self.delivery.send(normalized, otp, idempotency_key=f"otp:{challenge.id}:0")
        return challenge, should_deliver

    async def resend(self, challenge_id: UUID) -> OtpChallenge:
        challenge = await self._challenge(challenge_id, for_update=True)
        now = utc_now()
        if (
            challenge.consumed_at is not None
            or challenge.verified_at is not None
            or as_utc(challenge.expires_at) <= now
        ):
            raise InvalidOtpError("Verification challenge is no longer valid")
        if challenge.resend_count >= challenge.max_resends:
            raise RateLimitError("OTP resend limit reached")
        if as_utc(challenge.resend_available_at) > now:
            retry_after = max(1, int((as_utc(challenge.resend_available_at) - now).total_seconds()))
            raise RateLimitError("Please wait before requesting another code", details={"retry_after": retry_after})
        should_deliver = True
        if self.delivery is None:
            raise OtpDeliveryUnavailableError("OTP delivery is temporarily unavailable")
        otp = f"{secrets.randbelow(1_000_000):06d}"
        challenge.otp_hash = hash_password(otp)
        challenge.expires_at = now + timedelta(minutes=self.settings.auth_otp_expiry_minutes)
        challenge.resend_available_at = now + timedelta(
            seconds=self.settings.auth_otp_resend_seconds
        )
        challenge.resend_count += 1
        challenge.attempts = 0
        if should_deliver and self.delivery is not None:
            await self.delivery.send(
                challenge.identifier,
                otp,
                idempotency_key=f"otp:{challenge.id}:{challenge.resend_count}",
            )
        return challenge

    async def verify(
        self, challenge_id: UUID, otp: str, *, device_name: str | None = None
    ) -> dict[str, Any]:
        challenge = await self._challenge(challenge_id, for_update=True)
        now = utc_now()
        if (
            challenge.consumed_at is not None
            or challenge.verified_at is not None
            or as_utc(challenge.expires_at) <= now
        ):
            raise InvalidOtpError("The verification code is invalid or expired")
        if challenge.attempts >= challenge.max_attempts:
            challenge.consumed_at = now
            raise InvalidOtpError("The verification code is invalid or expired")
        challenge.attempts += 1
        if not verify_password(otp, challenge.otp_hash):
            if challenge.attempts >= challenge.max_attempts:
                challenge.consumed_at = now
            raise InvalidOtpError("The verification code is invalid or expired")
        challenge.verified_at = now
        user = await self._user_for_identifier(challenge.identifier)
        if user is not None:
            challenge.consumed_at = now
            tokens = await SessionService(self.session, self.settings).issue(
                user, device_name=device_name
            )
            return {**tokens, "registration_required": False}
        if challenge.purpose != OtpPurpose.REGISTRATION:
            challenge.consumed_at = now
            raise InvalidOtpError("The verification code is invalid or expired")
        email_val = challenge.identifier if "@" in challenge.identifier else None
        registration_token = create_registration_token(
            challenge_id=challenge.id,
            subject=challenge.identifier,
            email=email_val,
            secret=self.settings.auth_otp_secret.get_secret_value(),
        )
        return {
            "registration_required": True,
            "registration_token": registration_token,
            "email": email_val,
        }

    async def _challenge(self, challenge_id: UUID, *, for_update: bool) -> OtpChallenge:
        query = select(OtpChallenge).where(OtpChallenge.id == challenge_id)
        if for_update:
            query = query.with_for_update()
        row = await self.session.scalar(query)
        if row is None:
            raise InvalidOtpError("The verification code is invalid or expired")
        return row

    async def _user_for_identifier(self, identifier: str) -> User | None:
        if "@" in identifier:
            return await self.session.scalar(
                select(User).where(func.lower(User.email) == identifier.lower(), User.is_active.is_(True))
            )
        merchant = await self.session.scalar(
            select(Merchant).where(
                or_(Merchant.phone_number == identifier, Merchant.phone_number == f"+{identifier}")
            )
        )
        if merchant is None:
            return None
        return await self.session.scalar(
            select(User).where(User.merchant_id == merchant.id, User.is_active.is_(True))
        )

    async def _user_for_phone(self, phone: str) -> User | None:
        return await self._user_for_identifier(phone)


class OAuthTokenVerifier:
    _CONFIG = {
        OAuthProvider.GOOGLE: (
            "https://www.googleapis.com/oauth2/v3/certs",
            ("https://accounts.google.com", "accounts.google.com"),
        ),
        OAuthProvider.APPLE: (
            "https://appleid.apple.com/auth/keys",
            ("https://appleid.apple.com",),
        ),
    }

    async def verify(
        self,
        provider: OAuthProvider,
        id_token: str,
        *,
        client_id: str,
        nonce: str,
    ) -> dict[str, Any]:
        jwks_url, issuers = self._CONFIG[provider]
        try:
            header = jwt.get_unverified_header(id_token)
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
            keys = response.json().get("keys", [])
            jwk = next(item for item in keys if item.get("kid") == header.get("kid"))
            public_key = jwt.PyJWK.from_dict(jwk).key
            claims = jwt.decode(
                id_token,
                public_key,
                algorithms=[header.get("alg", "RS256")],
                audience=client_id,
                issuer=issuers,
                options={"require": ["sub", "iss", "aud", "exp", "iat"]},
            )
        except Exception as exc:
            raise OAuthCredentialError("OAuth credential is invalid or expired") from exc
        claimed_nonce = claims.get("nonce")
        allowed_nonces = {nonce, token_digest(nonce)}
        if claimed_nonce not in allowed_nonces:
            raise OAuthCredentialError("OAuth credential nonce is invalid")
        if provider == OAuthProvider.GOOGLE and claims.get("email_verified") is not True:
            raise OAuthCredentialError("Google email is not verified")
        return claims

    async def exchange_google_code(
        self,
        code: str,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if response.status_code != 200:
                raise OAuthCredentialError("Failed to exchange Google authorization code")
            return response.json()


class OAuthService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        verifier: OAuthTokenVerifier,
    ) -> None:
        self.session = session
        self.settings = settings
        self.verifier = verifier

    def client_id(self, provider: OAuthProvider) -> str:
        client_id = {
            OAuthProvider.GOOGLE: self.settings.google_oauth_client_id,
            OAuthProvider.APPLE: self.settings.apple_oauth_client_id,
        }[provider]
        if not client_id:
            raise ProviderError(f"{provider.value.title()} OAuth is not configured")
        return client_id

    def client_secret(self, provider: OAuthProvider) -> str | None:
        if provider == OAuthProvider.GOOGLE and self.settings.google_oauth_client_secret:
            return self.settings.google_oauth_client_secret.get_secret_value()
        return None

    async def start(self, provider: OAuthProvider) -> tuple[OAuthChallenge, str, str, str]:
        client_id = self.client_id(provider)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        challenge = OAuthChallenge(
            provider=provider,
            state_hash=token_digest(state),
            nonce_hash=token_digest(nonce),
            expires_at=utc_now() + timedelta(minutes=10),
        )
        self.session.add(challenge)
        await self.session.flush()
        return challenge, state, nonce, client_id

    async def exchange(
        self,
        provider: OAuthProvider,
        *,
        challenge_id: UUID,
        state: str,
        nonce: str,
        id_token: str | None = None,
        code: str | None = None,
        redirect_uri: str | None = None,
        device_name: str | None = None,
        link_user_id: UUID | None = None,
    ) -> dict[str, Any]:
        challenge = await self.session.scalar(
            select(OAuthChallenge)
            .where(OAuthChallenge.id == challenge_id, OAuthChallenge.provider == provider)
            .with_for_update()
        )
        now = utc_now()
        if (
            challenge is None
            or challenge.consumed_at is not None
            or as_utc(challenge.expires_at) <= now
            or not hmac.compare_digest(challenge.state_hash, token_digest(state))
            or not hmac.compare_digest(challenge.nonce_hash, token_digest(nonce))
        ):
            raise OAuthCredentialError("OAuth authorization state is invalid or expired")

        if not id_token and code:
            secret = self.client_secret(provider)
            if not secret:
                raise ProviderError(f"{provider.value.title()} OAuth client secret is not configured")
            effective_redirect = (
                redirect_uri
                or self.settings.google_oauth_redirect_uri
                or "http://localhost:8000/api/v1/auth/oauth/google/callback"
            )
            token_payload = await self.verifier.exchange_google_code(
                code,
                client_id=self.client_id(provider),
                client_secret=secret,
                redirect_uri=effective_redirect,
            )
            id_token = token_payload.get("id_token")

        if not id_token:
            raise OAuthCredentialError("Missing OAuth id_token or valid authorization code")

        claims = await self.verifier.verify(
            provider,
            id_token,
            client_id=self.client_id(provider),
            nonce=nonce,
        )
        subject = str(claims["sub"])
        email = str(claims["email"]).lower() if claims.get("email") else None
        identity = await self.session.scalar(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == provider,
                OAuthIdentity.provider_subject == subject,
            )
        )
        if link_user_id is not None:
            if identity is not None and identity.user_id != link_user_id:
                raise ConflictError("This OAuth identity is linked to another account")
            user = await self.session.get(User, link_user_id)
            if user is None:
                raise AuthenticationError("User no longer exists")
            if identity is None:
                self.session.add(
                    OAuthIdentity(
                        user_id=user.id,
                        provider=provider,
                        provider_subject=subject,
                        email=email,
                    )
                )
            challenge.consumed_at = now
            return {"linked": True, "provider": provider}
        if identity is not None:
            user = await self.session.get(User, identity.user_id)
            if user is None or not user.is_active:
                raise AuthenticationError("OAuth account is inactive")
            challenge.consumed_at = now
            return {
                **await SessionService(self.session, self.settings).issue(
                    user, device_name=device_name
                ),
                "registration_required": False,
            }
        user = (
            await self.session.scalar(select(User).where(func.lower(User.email) == email))
            if email
            else None
        )
        if user is not None:
            self.session.add(
                OAuthIdentity(
                    user_id=user.id,
                    provider=provider,
                    provider_subject=subject,
                    email=email,
                )
            )
            user.is_email_verified = True
            challenge.consumed_at = now
            return {
                **await SessionService(self.session, self.settings).issue(
                    user, device_name=device_name
                ),
                "registration_required": False,
            }
        if not email:
            raise OAuthCredentialError("OAuth provider did not supply a verified email")
        challenge.verified_at = now
        return {
            "registration_required": True,
            "registration_token": create_registration_token(
                challenge_id=challenge.id,
                subject=subject,
                email=email,
                provider=provider,
                secret=self.settings.auth_otp_secret.get_secret_value(),
            ),
            "email": email,
        }


class RegistrationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def register(
        self,
        *,
        email: str,
        business_name: str,
        store_name: str,
        registration_token: str,
        password: str | None,
        phone_number: str | None,
        address: dict[str, Any],
        device_name: str | None,
    ) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                registration_token,
                self.settings.auth_otp_secret.get_secret_value(),
                algorithms=["HS256"],
                options={"require": ["sub", "challenge_id", "provider", "exp", "iat"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Registration authorization is invalid or expired") from exc
        if claims.get("type") != "registration":
            raise AuthenticationError("Registration authorization is invalid")
        provider = str(claims["provider"])
        challenge_id = UUID(str(claims["challenge_id"]))
        normalized_email = email.strip().lower()
        existing = await self.session.scalar(
            select(User).where(func.lower(User.email) == normalized_email)
        )
        if existing is not None:
            raise ConflictError("An account already exists for this email")

        oauth_subject: str | None = None
        if provider == "OTP":
            challenge = await self.session.scalar(
                select(OtpChallenge).where(OtpChallenge.id == challenge_id).with_for_update()
            )
            if (
                challenge is None
                or challenge.verified_at is None
                or challenge.consumed_at is not None
                or challenge.purpose != OtpPurpose.REGISTRATION
                or challenge.identifier != claims["sub"]
            ):
                raise AuthenticationError("Registration verification is invalid")
            normalized_phone = normalize_phone(phone_number or "")
            if normalized_phone != challenge.identifier:
                raise AuthenticationError("Verified phone does not match registration")
            if not password:
                raise ValueError("Password is required for phone registration")
            challenge.consumed_at = utc_now()
            email_verified = False
            phone_verified = True
        else:
            challenge = await self.session.scalar(
                select(OAuthChallenge).where(OAuthChallenge.id == challenge_id).with_for_update()
            )
            if challenge is None or challenge.verified_at is None or challenge.consumed_at is not None:
                raise AuthenticationError("OAuth registration authorization is invalid")
            if claims.get("email") != normalized_email:
                raise AuthenticationError("OAuth email does not match registration")
            challenge.consumed_at = utc_now()
            normalized_phone = normalize_phone(phone_number) if phone_number else None
            oauth_subject = str(claims["sub"])
            email_verified = True
            phone_verified = False

        if normalized_phone:
            duplicate_phone = await self.session.scalar(
                select(Merchant.id).where(
                    or_(
                        Merchant.phone_number == normalized_phone,
                        Merchant.phone_number == f"+{normalized_phone}",
                    )
                )
            )
            if duplicate_phone is not None:
                raise ConflictError("An account already exists for this phone number")
        merchant = Merchant(name=business_name, phone_number=normalized_phone)
        self.session.add(merchant)
        await self.session.flush()
        user = User(
            merchant_id=merchant.id,
            email=normalized_email,
            password_hash=hash_password(password) if password else None,
            role="owner",
            is_email_verified=email_verified,
            is_phone_verified=phone_verified,
        )
        self.session.add(user)
        self.session.add(
            Store(
                merchant_id=merchant.id,
                name=store_name,
                address=address,
            )
        )
        await self.session.flush()
        if oauth_subject is not None:
            self.session.add(
                OAuthIdentity(
                    user_id=user.id,
                    provider=provider,
                    provider_subject=oauth_subject,
                    email=normalized_email,
                )
            )
        return await SessionService(self.session, self.settings).issue(
            user, device_name=device_name
        )
