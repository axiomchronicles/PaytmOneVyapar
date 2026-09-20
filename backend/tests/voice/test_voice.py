import re
from uuid import uuid4

import pytest

from app.channels.voice.agent import VoiceMunimAgent
from app.channels.voice.pipeline import extract_voice_intent
from app.channels.voice.protocol import VoiceIntentType
from app.channels.voice.sarvam import (
    clean_text_for_natural_voice,
    normalize_stt_language,
    resolve_target_language,
    sanitize_urdu_to_hindi,
)
from app.channels.voice.session import VoiceSession
from app.channels.whatsapp.approval_handler import (
    WhatsAppApprovalAction,
    parse_approval_callback,
)


def test_hinglish_voice_intents_are_structured() -> None:
    low = extract_voice_intent("bhaiya cold drink kal khatam ho jayegi")
    order = extract_voice_intent("teen peti aur mangwa do")
    approve = extract_voice_intent("haan kar do")
    modify = extract_voice_intent("do hi crates rakhna")
    assert low.intent == VoiceIntentType.REPORT_LOW_STOCK
    assert order.intent == VoiceIntentType.REQUEST_PURCHASE and order.quantity == 3
    assert approve.intent == VoiceIntentType.APPROVE_ACTIVE_PROPOSAL
    assert modify.intent == VoiceIntentType.MODIFY_ACTIVE_PROPOSAL and modify.quantity == 2


def test_whatsapp_approval_callback_is_strictly_parsed() -> None:
    callback = parse_approval_callback("approval:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa:APPROVE")
    assert callback.action == WhatsAppApprovalAction.APPROVE


def test_conversational_intents_recognized() -> None:
    greeting1 = extract_voice_intent("hi munim kaise ho")
    greeting2 = extract_voice_intent("namaste munim ji")
    greeting3 = extract_voice_intent("kem cho")
    caps = extract_voice_intent("tum kya kar sakti ho")
    inv = extract_voice_intent("mera stock kitna hai")
    proposals = extract_voice_intent("pending approval kitne hain")
    general = extract_voice_intent("GST invoice kaise banti hai")

    assert greeting1.intent == VoiceIntentType.GREETING
    assert greeting2.intent == VoiceIntentType.GREETING
    assert greeting3.intent == VoiceIntentType.GREETING
    assert caps.intent == VoiceIntentType.CAPABILITIES
    assert inv.intent == VoiceIntentType.QUERY_INVENTORY
    assert proposals.intent == VoiceIntentType.QUERY_PROPOSALS
    assert general.intent == VoiceIntentType.GENERAL_QUERY


@pytest.mark.asyncio
async def test_voice_munim_agent_handles_greeting_fallback() -> None:
    agent = VoiceMunimAgent(llm_provider=None)
    session = VoiceSession(merchant_id=uuid4(), user_id=uuid4(), language_code="hi-IN")
    intent = extract_voice_intent("hi munim kaise ho")

    reply = await agent.handle(session, intent)
    assert "सुरक्षित व्यावसायिक कार्य" not in reply
    assert "safe business action" not in reply
    assert "नमस्ते" in reply or "मदद" in reply or "बढ़िया" in reply
    assert len(session.history) == 2
    assert session.history[0]["role"] == "user"
    assert session.history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_voice_munim_agent_handles_capabilities_fallback() -> None:
    agent = VoiceMunimAgent(llm_provider=None)
    session = VoiceSession(merchant_id=uuid4(), user_id=uuid4(), language_code="en-IN")
    intent = extract_voice_intent("who are you")

    reply = await agent.handle(session, intent)
    assert "safe business action" not in reply
    assert "Munim" in reply


def test_clean_text_for_natural_voice_strips_markdown() -> None:
    raw = "**Namaste!** I am your *AI Munim*.\n- Item 1: Stock is good;\n- Item 2: Cold drinks."
    cleaned = clean_text_for_natural_voice(raw)
    assert "**" not in cleaned
    assert "*" not in cleaned
    assert ";" not in cleaned
    assert "Namaste! I am your AI Munim." in cleaned


class MockLLM:
    def __init__(self, output: str, should_fail: bool = False):
        self.output = output
        self.should_fail = should_fail

    async def generate(self, messages):
        if self.should_fail:
            raise RuntimeError("LLM network timeout")
        return self.output


@pytest.mark.asyncio
async def test_voice_munim_agent_uses_llm_when_available() -> None:
    mock_llm = MockLLM("Namaste Ramesh ji! Main badhiya hoon. Aaj dukan mein 2 items low stock hain.")
    agent = VoiceMunimAgent(llm_provider=mock_llm)
    session = VoiceSession(merchant_id=uuid4(), user_id=uuid4(), language_code="hi-IN")
    intent = extract_voice_intent("hi munim kaise ho")

    reply = await agent.handle(session, intent)
    assert "Namaste Ramesh ji" in reply
    assert len(session.history) == 2


@pytest.mark.asyncio
async def test_voice_munim_agent_gracefully_falls_back_on_llm_failure() -> None:
    failing_llm = MockLLM("", should_fail=True)
    agent = VoiceMunimAgent(llm_provider=failing_llm)
    session = VoiceSession(merchant_id=uuid4(), user_id=uuid4(), language_code="hi-IN")
    intent = extract_voice_intent("hi munim kaise ho")

    reply = await agent.handle(session, intent)
    assert "safe business action" not in reply
    assert "सुरक्षित व्यावसायिक कार्य" not in reply
    assert len(session.history) == 2


def test_sanitize_urdu_to_hindi_converts_nastaliq() -> None:
    urdu_phrase = "اچھا تو مجھے بتا سکتے ہیں آج کوئی vendor وغیرہ ہے"
    hindi_converted = sanitize_urdu_to_hindi(urdu_phrase)

    assert "अच्छा" in hindi_converted
    assert "मुझे" in hindi_converted
    assert "सकते" in hindi_converted
    assert "हैं" in hindi_converted
    assert "vendor" in hindi_converted
    assert "वगैरह" in hindi_converted
    assert "है" in hindi_converted
    # Verify no Perso-Arabic characters remain
    assert not re.search(r"[\u0600-\u06FF]", hindi_converted)


def test_clean_text_for_natural_voice_strips_perso_arabic() -> None:
    text_with_urdu = "Namaste! اچھا تو vendor ki details batao."
    cleaned = clean_text_for_natural_voice(text_with_urdu)
    assert not re.search(r"[\u0600-\u06FF]", cleaned)
    assert "Namaste!" in cleaned


def test_normalize_stt_language_maps_auto_to_hindi() -> None:
    assert normalize_stt_language("auto") == "hi-IN"
    assert normalize_stt_language(None) == "hi-IN"
    assert normalize_stt_language("") == "hi-IN"
    assert normalize_stt_language("hi") == "hi-IN"
    assert normalize_stt_language("en-IN") == "en-IN"
    assert normalize_stt_language("gu") == "gu-IN"


def test_resolve_target_language_handles_urdu_safely() -> None:
    # Text with Urdu characters must map to hi-IN so bulbul:v3 works
    assert resolve_target_language("اچھا تو mujhe batao", "auto") == "hi-IN"
    assert resolve_target_language("Hello store owner", "en-IN") == "en-IN"
    assert resolve_target_language("नमस्ते भैया", "hi-IN") == "hi-IN"



