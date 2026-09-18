from app.channels.voice.pipeline import extract_voice_intent
from app.channels.voice.protocol import VoiceIntentType
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
