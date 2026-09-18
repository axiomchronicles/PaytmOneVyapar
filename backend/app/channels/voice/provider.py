from collections.abc import AsyncIterator
from typing import Protocol

from app.channels.voice.protocol import VoiceEvent


class VoiceProvider(Protocol):
    async def transcribe(
        self,
        audio: AsyncIterator[bytes],
        *,
        language_code: str,
        sample_rate: int,
        encoding: str,
    ) -> AsyncIterator[VoiceEvent]: ...

    async def synthesize(self, text: str, *, language_code: str) -> AsyncIterator[VoiceEvent]: ...
