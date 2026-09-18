# Authentication flow

## Password and session lifecycle

Password login verifies the Argon2 hash and creates an access JWT plus an opaque refresh token. Only the refresh-token SHA-256 digest is stored. Flutter stores both in secure storage. A 401 causes one synchronized rotation; the old refresh session is revoked and linked to its replacement. Failed rotation clears secure storage and returns to authentication.

## OTP

OTP request normalizes the phone, applies identifier/IP hourly limits, stores only an Argon2 hash, and sends through the configured provider. Challenges enforce five-minute expiry, attempt limit, resend cooldown/count, and successful-verification replay prevention. Existing merchants receive a session; verified new numbers receive a short-lived registration token consumed by registration.

## Registration

Registration locks and consumes verified OTP/OAuth state, checks duplicate normalized email/phone, validates password strength where applicable, and creates User, Merchant, Store, and refresh session in one transaction. OAuth-created users have no fake password.

## Google and Apple

The backend creates state/nonce challenges. Flutter invokes the platform provider with the public client ID and returns only the provider ID token plus challenge values. FastAPI resolves current JWKS and verifies signature, issuer, audience, expiry, nonce, and verified email before login/link/registration. Client secrets never enter Flutter. Required environment values are `GOOGLE_OAUTH_CLIENT_ID` and `APPLE_OAUTH_CLIENT_ID`; platform console/bundle configuration remains external.
