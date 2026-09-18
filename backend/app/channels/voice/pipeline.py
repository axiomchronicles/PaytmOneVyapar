import re
from collections.abc import AsyncIterator, Awaitable, Callable

from app.channels.voice.protocol import VoiceEvent, VoiceEventType, VoiceIntent, VoiceIntentType
from app.channels.voice.provider import VoiceProvider
from app.channels.voice.session import VoiceSession

ActionHandler = Callable[[VoiceSession, VoiceIntent], Awaitable[str]]

_NUMBER_WORDS = {
    # English & Hindi/Hinglish
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "ek": 1,
    "do": 2,
    "teen": 3,
    "char": 4,
    "chaar": 4,
    "paanch": 5,
    "एक": 1,
    "दो": 2,
    "तीन": 3,
    "चार": 4,
    "पाँच": 5,
    "पांच": 5,
    # Gujarati
    "be": 2,
    "tran": 3,
    "એક": 1,
    "બે": 2,
    "ત્રણ": 3,
    "ચાર": 4,
    "પાંચ": 5,
    # Bengali
    "dui": 2,
    "tin": 3,
    "এক": 1,
    "দুই": 2,
    "তিন": 3,
    "চার": 4,
    "পাঁচ": 5,
    # Bhojpuri
    "du": 2,
    "दू": 2,
    # Tamil
    "ondru": 1,
    "irandu": 2,
    "moondru": 3,
    "naangu": 4,
    "aindhu": 5,
    "ஒன்று": 1,
    "இரண்டு": 2,
    "மூன்று": 3,
    "நான்கு": 4,
    "ஐந்து": 5,
    # Telugu
    "okati": 1,
    "rendu": 2,
    "moodu": 3,
    "naalugu": 4,
    "aidu": 5,
    "ఒకటి": 1,
    "రెండు": 2,
    "మూడు": 3,
    "నాలుగు": 4,
    "ఐదు": 5,
    # Marathi
    "don": 2,
    "paach": 5,
    "दोन": 2,
    "पाच": 5,
}


def _match_word(word: str, text: str) -> bool:
    if word.isascii():
        return bool(re.search(rf"\b{re.escape(word)}\b", text))
    return word in text


def extract_voice_intent(text: str) -> VoiceIntent:
    normalized = text.lower().strip()
    matches = [
        (match.start(), value)
        for word, value in _NUMBER_WORDS.items()
        if (
            match := (
                re.search(rf"\b{re.escape(word)}\b", normalized)
                if word.isascii()
                else re.search(re.escape(word), normalized)
            )
        )
    ]
    quantity = min(matches)[1] if matches else None
    numeric = re.search(r"\b(\d+)\b", normalized)
    quantity = int(numeric.group(1)) if numeric else quantity
    unit = (
        "crate"
        if any(
            _match_word(word, normalized)
            for word in (
                "peti",
                "crate",
                "crates",
                "पेटी",
                "પેટી",
                "ક્રેટ",
                "પેટીઓ",
                "পেটি",
                "பெட்டி",
                "பெட்டிகள்",
                "పెట్టె",
                "పెట్టెలు",
                "पेट्या",
                "पेटिया",
            )
        )
        else None
    )
    sku_hint = (
        "cold drink"
        if any(
            _match_word(word, normalized)
            for word in (
                "cold drink",
                "cola",
                "कोल्ड ड्रिंक",
                "કોલ્ડ ડ્રિંક",
                "કૉલ્ડ ડ્રિંક",
                "কোল্ড ড্রিঙ্ক",
                "கோல்ட் டிரிங்க்",
                "కోల్డ్ డ్రింక్",
            )
        )
        else None
    )

    if any(
        _match_word(phrase, normalized)
        for phrase in (
            "haan kar do",
            "approve",
            "confirm kar",
            "confirm",
            "manzoor",
            "anumodan",
            "aamam",
            "avunu",
            "स्वीकृत",
            "मंजूर",
            "हाँ",
            "હા કન્ફર્મ",
            "હા કરો",
            "হ্যাঁ",
            "ஆமாம்",
            "உறுதி",
            "அவுனு",
            "అవును",
            "ఆమోదించండి",
            "కన్ఫర్మ్",
            "कन्फर्म",
            "हो करा",
            "मंजूर करा",
        )
    ):
        intent = VoiceIntentType.APPROVE_ACTIVE_PROPOSAL
        explicit = True
    elif any(
        _match_word(word, normalized)
        for word in (
            "reject",
            "mat karo",
            "cancel",
            "nako",
            "vendaam",
            "oddu",
            "বাতিল",
            "રદ",
            "रद्द",
            "வேண்டாம்",
            "వద్దు",
            "नको",
        )
    ):
        intent = VoiceIntentType.REJECT_ACTIVE_PROPOSAL
        explicit = True
    elif quantity and any(
        _match_word(word, normalized)
        for word in (
            "rakhna",
            "modify",
            "badal",
            "rakho",
            "rakhjo",
            "parivartan",
            "மாற்று",
            "మార్చండి",
            "बदला",
            "বদলাও",
        )
    ):
        intent = VoiceIntentType.MODIFY_ACTIVE_PROPOSAL
        explicit = True
    elif any(
        _match_word(word, normalized)
        for word in (
            "mangwa",
            "order",
            "manga",
            "mangavi",
            "aniye",
            "theppinchandi",
            "pannunga",
            "magvoon",
            "मँगवा",
            "मंगवा",
            "મંગાવી",
            "ઓર્ડર",
            "আনিয়ে",
            "আনিয়া",
            "ஆர்டர்",
            "ఆర్డర్",
            "मागवून",
        )
    ):
        intent = VoiceIntentType.REQUEST_PURCHASE
        explicit = False
    elif any(
        _match_word(word, normalized)
        for word in (
            "khatam",
            "low",
            "kam",
            "ochho",
            "ochha",
            "khali",
            "shesh",
            "furiye",
            "sira gail",
            "theerndhadhu",
            "theerndhuvittadhu",
            "kuraivaga",
            "aypoindi",
            "thakkuva",
            "sampale",
            "कमी",
            "खतम",
            "खत्म",
            "सिरा",
            "सिरा गइल",
            "ઓછો",
            "ઓછા",
            "ખતમ",
            "શેષ",
            "শেষ",
            "குறைவு",
            "தீர்ந்து",
            "తక్కువ",
            "అయిపోయింది",
            "संपले",
        )
    ):
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
            yield VoiceEvent(
                type=VoiceEventType.AUDIO_START,
                language_code=session.language_code,
                audio_content_type=f"audio/{getattr(self.provider, 'tts_codec', 'unknown')}",
                metadata={
                    "text": response,
                    "codec": getattr(self.provider, "tts_codec", "unknown"),
                    "sample_rate": getattr(self.provider, "tts_sample_rate", None),
                    "channels": 1,
                },
            )
            async for audio_event in self.provider.synthesize(
                response, language_code=session.language_code
            ):
                if session.interrupted:
                    session.interrupted = False
                    break
                yield audio_event
            yield VoiceEvent(
                type=VoiceEventType.AUDIO_END,
                language_code=session.language_code,
            )
        session.close()
        yield VoiceEvent(type=VoiceEventType.SESSION_ENDED)
