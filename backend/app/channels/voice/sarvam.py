import asyncio
import base64
import re
from collections.abc import AsyncIterator

import httpx
import structlog

from app.channels.voice.protocol import VoiceEvent, VoiceEventType
from app.core.errors import ProviderError, SarvamAuthenticationError

logger = structlog.get_logger()


def _patch_websockets_drain_helper() -> None:
    """Fixes a concurrency bug in websockets.legacy.protocol._drain_helper.

    When multiple tasks call write_frame()/drain() concurrently on a paused connection
    (e.g., keepalive_ping, pong response to server ping, and audio streaming sends),
    websockets.legacy asserts that _drain_waiter is None, raising:
        AssertionError: assert waiter is None or waiter.cancelled()
    Instead of asserting, concurrent callers should await the existing drain waiter,
    matching modern websockets (asyncio) behavior.
    """
    try:
        from websockets.legacy.protocol import WebSocketCommonProtocol

        if getattr(WebSocketCommonProtocol, "_drain_helper_patched", False):
            return

        async def _safe_drain_helper(self: WebSocketCommonProtocol) -> None:
            if self.connection_lost_waiter.done():
                raise ConnectionResetError("Connection lost")
            if not self._paused:
                return
            waiter = getattr(self, "_drain_waiter", None)
            if waiter is not None and not waiter.done():
                await asyncio.shield(waiter)
                return
            waiter = self.loop.create_future()
            self._drain_waiter = waiter
            await waiter

        WebSocketCommonProtocol._drain_helper = _safe_drain_helper
        WebSocketCommonProtocol._drain_helper_patched = True
    except (ImportError, AttributeError):
        pass


_patch_websockets_drain_helper()


def _is_authentication_error(error: object) -> bool:
    text = str(error).lower()
    status = getattr(error, "status_code", None)
    return status in {401, 403} or any(
        marker in text
        for marker in ("invalid_subscription_key", "invalid credentials", "authentication")
    )


URDU_TO_HINDI_WORDS: dict[str, str] = {
    "اچھا": "अच्छा", "تو": "तो", "مجھے": "मुझे", "بتا": "बता", "سکتے": "सकते",
    "ہیں": "हैं", "آج": "आज", "کوئی": "कोई", "وغیرہ": "वगैरह", "ہے": "है",
    "جس": "जिस", "کے": "के", "ساتھ": "साथ", "میں": "में", "لین": "लेन",
    "دین": "देन", "کر": "कर", "سکتا": "सकता", "ہوں": "हूँ", "جی": "जी",
    "ابھی": "अभी", "آپ": "आप", "اسٹور": "स्टोर", "کسی": "किसी", "وینڈر": "वेंडर",
    "کی": "की", "نہیں": "नहीं", "اگر": "अगर", "خاص": "खास", "نام": "नाम",
    "بتائیں": "बताएं", "اس": "उस", "تفصیل": "तफसील", "چیک": "चेक", "کرنے": "करने",
    "مدد": "मदद", "دوں": "दूँ", "گی": "गी", "کا": "का", "کو": "को", "سے": "से",
    "پر": "पर", "تک": "तक", "یہ": "यह", "وہ": "वह", "کیا": "क्या", "کیوں": "क्यों",
    "کب": "कब", "کہاں": "कहाँ", "کیسے": "कैसे", "کتنا": "कितना", "مال": "माल",
    "اسٹاک": "स्टॉक", "خرید": "खरीद", "فروخت": "बिक्री", "آرڈر": "ऑर्डर",
    "دکان": "दुकान", "منظوری": "मंजूरी", "پینڈنگ": "पेंडिंग", "زیر التوا": "पेंडिंग",
    "موجود": "मौजूद", "شکریہ": "शुक्रिया", "سلام": "नमस्ते", "نمستے": "नमस्ते",
    "یا": "या", "زیر": "पेंडिंग", "التوا": "",
}

URDU_TO_HINDI_CHARS: dict[str, str] = {
    "ا": "अ", "آ": "आ", "ب": "ब", "پ": "प", "ت": "त", "ٹ": "ट", "ث": "स",
    "ج": "ज", "چ": "च", "ح": "ह", "خ": "ख", "د": "द", "ڈ": "ड", "ذ": "ज़",
    "ر": "र", "ڑ": "ड़", "ز": "ज़", "ژ": "ज़", "س": "स", "ش": "श", "ص": "स",
    "ض": "ज़", "ط": "त", "ظ": "ज़", "ع": "अ", "غ": "ग़", "ف": "फ", "ق": "क",
    "ک": "क", "گ": "ग", "ل": "ल", "م": "म", "ن": "न", "ں": "ं", "و": "ो",
    "ہ": "ह", "ھ": "ह", "ء": "", "ی": "ी", "ے": "े", "؟": "?", "،": ",",
    "۔": ".", "ئ": "ई", "ۂ": "ह", "ۃ": "त", "ۆ": "ओ",
}


def sanitize_urdu_to_hindi(text: str) -> str:
    """Converts Perso-Arabic / Urdu script into Devanagari Hindi.

    Sarvam saaras:v4 in auto mode or Hinglish occasionally detects Urdu and emits
    Nastaliq script. This converts it back to readable Devanagari Hindi so Sarvam
    bulbul:v3 TTS does not fail with 400 Bad Request.
    """
    if not text or not re.search(r"[\u0600-\u06FF]", text):
        return text

    words = text.split()
    converted_words: list[str] = []
    for w in words:
        suffix = ""
        clean_w = w
        if clean_w and clean_w[-1] in "؟،.!,?":
            suffix = clean_w[-1]
            if suffix == "؟":
                suffix = "?"
            elif suffix == "،":
                suffix = ","
            elif suffix == "۔":
                suffix = "."
            clean_w = clean_w[:-1]

        if clean_w in URDU_TO_HINDI_WORDS:
            val = URDU_TO_HINDI_WORDS[clean_w]
            if val:
                converted_words.append(val + suffix)
        else:
            char_res = "".join(URDU_TO_HINDI_CHARS.get(c, c) for c in clean_w)
            converted_words.append(char_res + suffix)

    res = " ".join(converted_words)
    return re.sub(r"\s+", " ", res).strip()


def normalize_stt_language(lang: str | None) -> str:
    """Normalizes STT language code for Sarvam saaras:v4.

    Ensures 'auto' and unspecified languages map to 'hi-IN' so the model does not
    accidentally classify Hindustani speech as 'ur-IN' and output Nastaliq script.
    """
    code = (lang or "").strip().lower()
    if not code or code in ("auto", "und", "hi", "hi-in", "bho", "bho-in", "hi-bho"):
        return "hi-IN"
    if code.startswith("gu"):
        return "gu-IN"
    if code.startswith("bn"):
        return "bn-IN"
    if code.startswith("ta"):
        return "ta-IN"
    if code.startswith("te"):
        return "te-IN"
    if code.startswith("mr"):
        return "mr-IN"
    if code.startswith("en"):
        return "en-IN"
    if code.startswith("kn"):
        return "kn-IN"
    if code.startswith("ml"):
        return "ml-IN"
    if code.startswith("pa"):
        return "pa-IN"
    if code.startswith("or") or code.startswith("od"):
        return "or-IN"
    return "hi-IN"


def clean_text_for_natural_voice(text: str) -> str:
    """Prepares text for natural, smooth neural speech with human-like breathing pauses.

    Sarvam bulbul:v3 relies on punctuation for prosody and tone:
    - Transliterates any stray Urdu characters to Devanagari Hindi.
    - Strips markdown symbols (*, #, _, ~, `).
    - Multiple dots/dashes cause unnatural hesitation.
    - Semicolons and colons are softened to natural clause commas.
    - Whitespace is normalized.
    """
    cleaned = sanitize_urdu_to_hindi(text)
    # Strip any remaining Perso-Arabic/Urdu script characters to guarantee TTS compatibility
    cleaned = re.sub(r"[\u0600-\u06FF]", "", cleaned)
    cleaned = re.sub(r"[\*#_`~]", "", cleaned)
    cleaned = re.sub(r"^\s*[-•]\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = re.sub(r"-{2,}", " ", cleaned)
    cleaned = cleaned.replace(";", ",").replace(":", ",")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def resolve_target_language(text: str, language_code: str | None = None) -> str:
    """Resolves concrete BCP-47 language code for Sarvam TTS.

    bulbul:v3 requires a valid language code (cannot accept 'auto', 'und', or empty).
    If auto/unspecified, script detection inspects text to select the proper Indian language.
    """
    # If text contains Urdu/Arabic characters, target language MUST be Hindi
    if re.search(r"[\u0600-\u06FF]", text):
        return "hi-IN"

    lang = (language_code or "").strip().lower()
    if lang in ("bho-in", "bho", "hi-bho"):
        return "hi-IN"
    if lang.startswith("hi"):
        return "hi-IN"
    if lang.startswith("en"):
        return "en-IN"
    if lang.startswith("gu"):
        return "gu-IN"
    if lang.startswith("bn"):
        return "bn-IN"
    if lang.startswith("ta"):
        return "ta-IN"
    if lang.startswith("te"):
        return "te-IN"
    if lang.startswith("mr"):
        return "mr-IN"
    if lang.startswith("kn"):
        return "kn-IN"
    if lang.startswith("ml"):
        return "ml-IN"
    if lang.startswith("pa"):
        return "pa-IN"
    if lang.startswith("od"):
        return "od-IN"

    if re.search(r"[\u0A80-\u0AFF]", text):
        return "gu-IN"
    if re.search(r"[\u0980-\u09FF]", text):
        return "bn-IN"
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta-IN"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te-IN"
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn-IN"
    if re.search(r"[\u0D00-\u0D7F]", text):
        return "ml-IN"
    if re.search(r"[\u0A00-\u0A7F]", text):
        return "pa-IN"
    if re.search(r"[\u0B00-\u0B7F]", text):
        return "od-IN"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi-IN"

    return "en-IN"


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
        tts_codec: str = "linear16",
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
        stt_lang = normalize_stt_language(language_code)
        try:
            async with client.speech_to_text_realtime_streaming.connect(
                language_code=stt_lang,
                model=self.stt_model,
                stream_type="fast",
                mode="codemix",
                endpointing="vad",
                encoding=encoding,
                sample_rate=str(sample_rate),
                return_timestamps="true",
                threshold="0.35",
                prefix_padding_ms="300",
                silence_duration_ms="800",
                prompt="दुकानदार और ग्राहक की बातचीत, Paytm ONE Vyapar inventory billing",
            ) as socket:

                async def send_audio() -> None:
                    try:
                        async for chunk in audio:
                            if not chunk:
                                continue
                            raw_ws = getattr(socket, "_websocket", None)
                            if raw_ws is not None and getattr(raw_ws, "closed", False):
                                break
                            await socket.send_realtime_audio_input(
                                RealtimeAudioInput(audio=base64.b64encode(chunk).decode())
                            )
                        raw_ws = getattr(socket, "_websocket", None)
                        if raw_ws is not None and not getattr(raw_ws, "closed", False):
                            await socket.send_realtime_end(RealtimeEnd())
                    except (asyncio.CancelledError, GeneratorExit):
                        raise
                    except Exception as err:
                        logger.debug("sarvam_send_audio_stopped", error=str(err))

                message_queue: asyncio.Queue[object | None] = asyncio.Queue(maxsize=128)

                async def read_socket() -> None:
                    try:
                        async for message in socket:
                            await message_queue.put(message)
                    except (asyncio.CancelledError, GeneratorExit):
                        pass
                    except Exception as exc:
                        await message_queue.put(exc)
                    finally:
                        await message_queue.put(None)

                sender = asyncio.create_task(send_audio())
                reader = asyncio.create_task(read_socket())
                try:
                    while True:
                        item = await message_queue.get()
                        if item is None:
                            break
                        if isinstance(item, Exception):
                            raise item

                        message = item
                        event = getattr(message, "event", None)
                        if event == "transcript.partial":
                            sanitized = sanitize_urdu_to_hindi(message.text)
                            yield VoiceEvent(
                                type=VoiceEventType.TRANSCRIPT_PARTIAL,
                                text=sanitized,
                                language_code=message.language or stt_lang,
                            )
                        elif event == "transcript.final":
                            sanitized = sanitize_urdu_to_hindi(message.text)
                            yield VoiceEvent(
                                type=VoiceEventType.TRANSCRIPT_FINAL,
                                text=sanitized,
                                language_code=message.language or stt_lang,
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
                    if not reader.done():
                        reader.cancel()
                    await asyncio.gather(sender, reader, return_exceptions=True)
        except SarvamAuthenticationError:
            raise
        except ProviderError:
            raise
        except Exception as exc:
            if _is_authentication_error(exc):
                raise SarvamAuthenticationError() from exc
            logger.error(
                "sarvam_stt_failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise ProviderError("Voice transcription provider failed") from exc
        finally:
            await http_client.aclose()

    async def synthesize(self, text: str, *, language_code: str) -> AsyncIterator[VoiceEvent]:
        from sarvamai import AsyncSarvamAI
        from sarvamai.text_to_speech_streaming.socket_client import (
            ConfigureConnection,
            ConfigureConnectionData,
        )

        speech_text = clean_text_for_natural_voice(text)
        if not speech_text:
            return

        http_client = httpx.AsyncClient(timeout=60)
        client = AsyncSarvamAI(api_subscription_key=self.api_key, httpx_client=http_client)
        target_lang = resolve_target_language(speech_text, language_code)

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
                                language_code=target_lang,
                                metadata={
                                    "speaker": self.tts_speaker,
                                    "sample_rate": self.tts_sample_rate,
                                    "bitrate": self.tts_bitrate,
                                    "codec": self.tts_codec,
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
            logger.warning("sarvam_streaming_tts_fallback", error=str(exc), error_type=type(exc).__name__)
            # Resilient fallback: Stream via HTTP convert_stream for uninterrupted delivery
            try:
                stream = client.text_to_speech.convert_stream(
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
                            language_code=target_lang,
                            metadata={"fallback": True, "speaker": self.tts_speaker, "codec": self.tts_codec},
                        )
            except Exception as fallback_exc:
                if _is_authentication_error(fallback_exc):
                    logger.error("sarvam_authentication_failed", provider="sarvam")
                    raise SarvamAuthenticationError() from fallback_exc
                logger.error("sarvam_tts_fallback_failed", error=str(fallback_exc))
                raise ProviderError("Sarvam TTS synthesis failed") from fallback_exc
        finally:
            await http_client.aclose()
