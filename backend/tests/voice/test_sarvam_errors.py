import pytest

from app.channels.voice.sarvam import _is_authentication_error
from app.core.config import Settings
from app.core.errors import SarvamAuthenticationError


class ProviderResponseError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_sarvam_configuration_strips_transport_artifacts() -> None:
    settings = Settings(sarvam_api_key=' "credential-value"\n')
    assert settings.sarvam_api_key is not None
    assert settings.sarvam_api_key.get_secret_value() == "credential-value"


@pytest.mark.parametrize(
    "error",
    [
        ProviderResponseError("invalid_subscription_key"),
        ProviderResponseError("request denied", status_code=401),
    ],
)
def test_sarvam_authentication_errors_are_detected_without_exposing_key(error) -> None:
    assert _is_authentication_error(error)
    safe = SarvamAuthenticationError()
    assert safe.code == "SARVAM_AUTHENTICATION_FAILED"
    assert safe.message == "Voice service is temporarily unavailable."
