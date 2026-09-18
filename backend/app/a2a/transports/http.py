import asyncio
import time

import httpx

from app.a2a.schemas import A2AEnvelope
from app.a2a.signing import verify_envelope
from app.core.errors import ProviderAuthenticationError, ProviderError, ProviderTimeoutError
from app.infrastructure.observability.metrics import a2a_failures, a2a_latency


class HTTPA2ATransport:
    def __init__(self, client: httpx.AsyncClient, *, retries: int = 2) -> None:
        self.client = client
        self.retries = retries

    async def send(
        self, endpoint: str, envelope: A2AEnvelope, *, response_signing_secret: str
    ) -> A2AEnvelope:
        started = time.perf_counter()
        for attempt in range(self.retries + 1):
            try:
                response = await self.client.post(
                    endpoint,
                    json=envelope.model_dump(mode="json"),
                    headers={"Idempotency-Key": envelope.idempotency_key},
                )
                if response.status_code in {401, 403}:
                    raise ProviderAuthenticationError("Remote A2A agent rejected authentication")
                response.raise_for_status()
                result = A2AEnvelope.model_validate(response.json())
                verify_envelope(
                    result,
                    secret=response_signing_secret,
                    expected_receiver_id=str(envelope.sender_agent_id),
                )
                if result.sender_agent_id != envelope.receiver_agent_id:
                    raise ProviderAuthenticationError("A2A response sender does not match request")
                if result.correlation_id != envelope.correlation_id:
                    raise ProviderError("A2A response correlation does not match request")
                a2a_latency.record((time.perf_counter() - started) * 1000)
                return result
            except httpx.TimeoutException as exc:
                if attempt == self.retries:
                    a2a_failures.add(1, {"reason": "timeout"})
                    raise ProviderTimeoutError("Remote A2A agent timed out") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt == self.retries:
                    a2a_failures.add(1, {"reason": "http"})
                    raise ProviderError(
                        "Remote A2A agent failed", details={"status": exc.response.status_code}
                    ) from exc
            await asyncio.sleep(0.2 * (2**attempt))
        raise ProviderError("Remote A2A agent failed")
