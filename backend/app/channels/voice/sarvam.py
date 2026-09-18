import asyncio
import base64
from collections.abc import AsyncIterator

import httpx

from app.channels.voice.protocol import VoiceEvent, VoiceEventType
from app.core.errors import ProviderError


class SarvamVoiceProvider:
    def __init__(
        self, *, api_key: str, stt_model: str, tts_model: str, tts_speaker: str = "ritu"
    ) -> None:
        self.api_key = api_key
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.tts_speaker = tts_speaker

    async def transcribe(
        self,
        audio: AsyncIterator[bytes],
        *,
        language_code: str,
        sample_rate: int = 16000,
        encoding: str = "linear16",
    ) -> AsyncIterator[VoiceEvent]:
        from sarvamai import AsyncSarvamAI
        from sarvamai.types import RealtimeAudioInput, RealtimeEnd

        http_client = httpx.AsyncClient(timeout=60)
        client = AsyncSarvamAI(api_subscription_key=self.api_key, httpx_client=http_client)
        try:
            async with client.speech_to_text_realtime_streaming.connect(
                language_code=language_code,
                model=self.stt_model,
                stream_type="fast",
                mode="codemix",
                endpointing="vad",
                encoding=encoding,
                sample_rate=str(sample_rate),
                return_timestamps="true",
            ) as socket:

                async def send_audio() -> None:
                    async for chunk in audio:
                        await socket.send_realtime_audio_input(
                            RealtimeAudioInput(audio=base64.b64encode(chunk).decode())
                        )
                    await socket.send_realtime_end(RealtimeEnd())

                sender = asyncio.create_task(send_audio())
                try:
                    async for message in socket:
                        event = getattr(message, "event", None)
                        if event == "transcript.partial":
                            yield VoiceEvent(
                                type=VoiceEventType.TRANSCRIPT_PARTIAL,
                                text=message.text,
                                language_code=message.language or language_code,
                            )
                        elif event == "transcript.final":
                            yield VoiceEvent(
                                type=VoiceEventType.TRANSCRIPT_FINAL,
                                text=message.text,
                                language_code=message.language or language_code,
                                metadata={
                                    "utterance_index": message.utterance_idx,
                                    "start_s": message.start_s,
                                    "end_s": message.end_s,
                                },
                            )
                        elif event == "error" and message.is_fatal:
                            raise ProviderError(
                                "Sarvam realtime STT failed", details={"code": message.code}
                            )
                        elif event == "session.end":
                            break
                finally:
                    if not sender.done():
                        sender.cancel()
                    await asyncio.gather(sender, return_exceptions=True)
        finally:
            await http_client.aclose()

    async def synthesize(self, text: str, *, language_code: str) -> AsyncIterator[VoiceEvent]:
        from sarvamai import AsyncSarvamAI

        http_client = httpx.AsyncClient(timeout=60)
        client = AsyncSarvamAI(api_subscription_key=self.api_key, httpx_client=http_client)
        try:
            async with client.text_to_speech_streaming.connect(
                model=self.tts_model, send_completion_event="true"
            ) as socket:
                await socket.configure(
                    target_language_code=language_code,
                    speaker=self.tts_speaker,
                    speech_sample_rate=24000,
                    enable_preprocessing=True,
                    output_audio_codec="mp3",
                )
                await socket.convert(text)
                await socket.flush()
                async for message in socket:
                    if getattr(message, "type", None) == "audio":
                        yield VoiceEvent(
                            type=VoiceEventType.AUDIO,
                            audio=base64.b64decode(message.data.audio),
                            audio_content_type=message.data.content_type,
                            language_code=language_code,
                        )
                    elif getattr(message, "type", None) == "event":
                        if message.data.event_type == "final":
                            break
                    elif getattr(message, "type", None) == "error":
                        raise ProviderError("Sarvam streaming TTS failed")
        finally:
            await http_client.aclose()
