import re
from collections.abc import AsyncIterator, Awaitable, Callable

from app.channels.voice.protocol import VoiceEvent, VoiceEventType, VoiceIntent, VoiceIntentType
from app.channels.voice.provider import VoiceProvider
from app.channels.voice.session import VoiceSession

ActionHandler = Callable[[VoiceSession, VoiceIntent], Awaitable[str]]

_NUMBER_WORDS = {
    "ek": 1,
    "do": 2,
    "teen": 3,
    "char": 4,
    "chaar": 4,
    "paanch": 5,
    "one": 1,
    "two": 2,
    "three": 3,
}


def extract_voice_intent(text: str) -> VoiceIntent:
    normalized = text.lower().strip()
    matches = [
        (match.start(), value)
        for word, value in _NUMBER_WORDS.items()
        if (match := re.search(rf"\b{word}\b", normalized))
    ]
    quantity = min(matches)[1] if matches else None
    numeric = re.search(r"\b(\d+)\b", normalized)
    quantity = int(numeric.group(1)) if numeric else quantity
    unit = "crate" if any(word in normalized for word in ("peti", "crate")) else None
    sku_hint = "cold drink" if any(word in normalized for word in ("cold drink", "cola")) else None

    if any(phrase in normalized for phrase in ("haan kar do", "approve", "confirm kar")):
        intent = VoiceIntentType.APPROVE_ACTIVE_PROPOSAL
        explicit = True
    elif any(word in normalized for word in ("reject", "mat karo", "cancel")):
        intent = VoiceIntentType.REJECT_ACTIVE_PROPOSAL
        explicit = True
    elif quantity and any(word in normalized for word in ("rakhna", "modify", "badal")):
        intent = VoiceIntentType.MODIFY_ACTIVE_PROPOSAL
        explicit = True
    elif quantity and any(word in normalized for word in ("mangwa", "order", "manga")):
        intent = VoiceIntentType.REQUEST_PURCHASE
        explicit = False
    elif any(word in normalized for word in ("khatam", "low", "kam")):
        intent = VoiceIntentType.REPORT_LOW_STOCK
        explicit = False
    else:
        intent = VoiceIntentType.UNKNOWN
        explicit = False
    return VoiceIntent(
        intent=intent,
        quantity=quantity,
        unit=unit,
        sku_hint=sku_hint,
        explicit_confirmation=explicit,
        raw_text=text,
    )


class VoicePipeline:
    def __init__(self, provider: VoiceProvider, action_handler: ActionHandler) -> None:
        self.provider = provider
        self.action_handler = action_handler

    async def run(
        self, session: VoiceSession, audio: AsyncIterator[bytes]
    ) -> AsyncIterator[VoiceEvent]:
        yield VoiceEvent(type=VoiceEventType.SESSION_STARTED)
        async for event in self.provider.transcribe(
            audio,
            language_code=session.language_code,
            sample_rate=session.sample_rate,
            encoding=session.encoding,
        ):
            yield event
            if event.type != VoiceEventType.TRANSCRIPT_FINAL or not event.text:
                continue
            intent = extract_voice_intent(event.text)
            yield VoiceEvent(type=VoiceEventType.ACTION, metadata=intent.model_dump(mode="json"))
            response = await self.action_handler(session, intent)
            yield VoiceEvent(type=VoiceEventType.RESPONSE_TEXT, text=response)
            async for audio_event in self.provider.synthesize(
                response, language_code=session.language_code
            ):
                if session.interrupted:
                    session.interrupted = False
                    break
                yield audio_event
        session.close()
        yield VoiceEvent(type=VoiceEventType.SESSION_ENDED)
