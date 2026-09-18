import asyncio
import base64
import re
from collections.abc import AsyncIterator

import httpx
import structlog

from app.channels.voice.protocol import VoiceEvent, VoiceEventType
from app.core.errors import ProviderError, SarvamAuthenticationError

logger = structlog.get_logger()


def _is_authentication_error(error: object) -> bool:
    text = str(error).lower()
    status = getattr(error, "status_code", None)
    return status in {401, 403} or any(
        marker in text
        for marker in ("invalid_subscription_key", "invalid credentials", "authentication")
    )


def clean_text_for_natural_voice(text: str) -> str:
    """Prepares text for natural, smooth neural speech with human-like breathing pauses.

    Sarvam bulbul:v3 relies on punctuation for prosody and tone:
    - Multiple dots/dashes cause unnatural hesitation.
    - Semicolons and colons are softened to natural clause commas.
    - Whitespace is normalized.
    """
    cleaned = re.sub(r"\.{2,}", ".", text)
    cleaned = re.sub(r"-{2,}", " ", cleaned)
    cleaned = cleaned.replace(";", ",").replace(":", ",")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


class SarvamVoiceProvider:
    def __init__(
        self,
        *,
        api_key: str,
        stt_model: str,
        tts_model: str,
        tts_speaker: str = "ritu",
        tts_pace: float = 1.0,
        tts_temperature: float = 0.6,
        tts_sample_rate: int = 24000,
        tts_codec: str = "mp3",
        tts_bitrate: str = "192k",
        enable_preprocessing: bool = True,
        min_buffer_size: int = 60,
        max_chunk_length: int = 200,
    ) -> None:
        self.api_key = api_key
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.tts_speaker = tts_speaker
        self.tts_pace = tts_pace
        self.tts_temperature = tts_temperature
        self.tts_sample_rate = tts_sample_rate
        self.tts_codec = tts_codec
        self.tts_bitrate = tts_bitrate
        self.enable_preprocessing = enable_preprocessing
        self.min_buffer_size = min_buffer_size
        self.max_chunk_length = max_chunk_length

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
                            if _is_authentication_error(message.code):
                                raise SarvamAuthenticationError()
                            logger.error(
                                "sarvam_stt_provider_error",
                                provider_code=str(message.code)[:80],
                                provider_status=getattr(message, "status_code", None),
                                provider_message=str(getattr(message, "message", ""))[:200],
                            )
                            raise ProviderError("Voice transcription provider failed")
                        elif event == "session.end":
                            break
                finally:
                    if not sender.done():
                        sender.cancel()
                    await asyncio.gather(sender, return_exceptions=True)
        except SarvamAuthenticationError:
            raise
        except ProviderError:
            raise
        except Exception as exc:
            if _is_authentication_error(exc):
                raise SarvamAuthenticationError() from exc
            logger.error("sarvam_stt_failed", error_type=type(exc).__name__)
            raise ProviderError("Voice transcription provider failed") from exc
        finally:
            await http_client.aclose()

    async def synthesize(self, text: str, *, language_code: str) -> AsyncIterator[VoiceEvent]:
        from sarvamai import AsyncSarvamAI
        from sarvamai.text_to_speech_streaming.socket_client import (
            ConfigureConnection,
            ConfigureConnectionData,
        )

        http_client = httpx.AsyncClient(timeout=60)
        client = AsyncSarvamAI(api_subscription_key=self.api_key, httpx_client=http_client)
        # Normalize Bhojpuri or regional codes to Sarvam-supported TTS code:
        # Bhojpuri uses Devanagari text synthesized via hi-IN speaker
        target_lang = "hi-IN" if language_code in ("bho-IN", "bho", "hi-BHO") else language_code
        speech_text = clean_text_for_natural_voice(text)

        try:
            # Primary path: Low-latency WebSocket streaming with bulbul:v3 neural parameters
            async with client.text_to_speech_streaming.connect(
                model=self.tts_model, send_completion_event="true"
            ) as socket:
                # bulbul:v3 supports temperature (expressive natural prosody) and pace.
                # Pitch and loudness are omitted to prevent neural model distortion.
                config_data = ConfigureConnectionData(
                    model=self.tts_model,
                    language_code=target_lang,
                    speaker=self.tts_speaker,
                    pace=self.tts_pace,
                    temperature=self.tts_temperature,
                    speech_sample_rate=self.tts_sample_rate,
                    enable_preprocessing=self.enable_preprocessing,
                    output_audio_codec=self.tts_codec,
                    output_audio_bitrate=self.tts_bitrate,
                    min_buffer_size=self.min_buffer_size,
                    max_chunk_length=self.max_chunk_length,
                )
                await socket._send_model(ConfigureConnection(data=config_data))
                await socket.convert(speech_text)
                await socket.flush()

                async for message in socket:
                    msg_type = getattr(message, "type", None)
                    if msg_type == "audio":
                        audio_data = getattr(message, "data", None)
                        if audio_data and getattr(audio_data, "audio", None):
                            yield VoiceEvent(
                                type=VoiceEventType.AUDIO,
                                audio=base64.b64decode(audio_data.audio),
                                audio_content_type=getattr(
                                    audio_data, "content_type", f"audio/{self.tts_codec}"
                                ),
                                language_code=language_code,
                                metadata={
                                    "speaker": self.tts_speaker,
                                    "sample_rate": self.tts_sample_rate,
                                    "bitrate": self.tts_bitrate,
                                },
                            )
                    elif msg_type == "event":
                        event_data = getattr(message, "data", None)
                        if event_data and getattr(event_data, "event_type", None) == "final":
                            break
                    elif msg_type == "error":
                        err_data = getattr(message, "data", None)
                        raise ProviderError(
                            "Sarvam streaming TTS failed",
                            details={"error": getattr(err_data, "message", str(message))},
                        )
        except Exception as exc:
            if _is_authentication_error(exc):
                logger.error("sarvam_authentication_failed", provider="sarvam")
                raise SarvamAuthenticationError() from exc
            logger.warning("sarvam_streaming_tts_fallback", error_type=type(exc).__name__)
            # Resilient fallback: Stream via HTTP convert_stream for uninterrupted delivery
            try:
                stream = await client.text_to_speech.convert_stream(
                    text=speech_text,
                    language_code=target_lang,
                    speaker=self.tts_speaker,
                    model=self.tts_model,
                    temperature=self.tts_temperature,
                    pace=self.tts_pace,
                    speech_sample_rate=self.tts_sample_rate,
                    output_audio_codec=self.tts_codec,
                    output_audio_bitrate=self.tts_bitrate,
                    enable_preprocessing=self.enable_preprocessing,
                )
                async for chunk in stream:
                    if chunk:
                        yield VoiceEvent(
                            type=VoiceEventType.AUDIO,
                            audio=chunk,
                            audio_content_type=f"audio/{self.tts_codec}",
                            language_code=language_code,
                            metadata={"fallback": True, "speaker": self.tts_speaker},
                        )
            except Exception as fallback_exc:
                if _is_authentication_error(fallback_exc):
                    logger.error("sarvam_authentication_failed", provider="sarvam")
                    raise SarvamAuthenticationError() from fallback_exc
                raise ProviderError("Sarvam TTS synthesis failed") from fallback_exc
        finally:
            await http_client.aclose()
