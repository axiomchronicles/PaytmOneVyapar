import asyncio
from typing import Any
from uuid import UUID

import structlog

from app.channels.voice.i18n import get_voice_message
from app.channels.voice.protocol import VoiceIntent, VoiceIntentType
from app.channels.voice.sarvam import clean_text_for_natural_voice, sanitize_urdu_to_hindi
from app.channels.voice.session import VoiceSession
from app.domain.enums import ApprovalStatus
from app.integrations.llm.base import DisabledLLMProvider

logger = structlog.get_logger()

VOICE_MUNIM_SYSTEM_PROMPT = """You are "Voice Munim" (also known as Ritu), a warm, respectful, and highly competent AI shop manager and business assistant for Indian kirana and retail merchants on Paytm ONE Vyapar.

Your job is to talk with the merchant over live voice, understand their questions or instructions, and help them run their retail shop smoothly.

CRITICAL VOICE CONSTRAINTS:
1. Spoken Audio Delivery: Your response will be synthesized directly into spoken audio using a neural voice engine. Keep your responses concise (1 to 3 natural sentences maximum). Never generate long paragraphs or essays.
2. Plain Text Only: Do NOT use markdown symbols, asterisks (** or *), hashes (#), bullet points (- or •), numbered lists, emojis, or tables. Output plain, spoken-friendly sentences with clear commas and periods for natural breathing pauses.
3. Natural Language & Tone:
   - Match the merchant's spoken language naturally (e.g. Hinglish, Hindi, Gujarati, Bengali, Bhojpuri, Tamil, Telugu, Marathi, or English).
   - If the merchant speaks Hinglish (like "hi munim kaise ho"), reply in warm, natural conversational Hinglish (e.g. "नमस्ते भैया! मैं बिल्कुल ठीक हूँ। आपकी दुकान में आज क्या चल रहा है?").
   - Address the merchant respectfully with "ji", "aap", "namaste".
4. SCRIPT & SCRIPT COMPATIBILITY:
   - STRICT PROHIBITION: NEVER reply in Urdu, Perso-Arabic script, or Nastaliq (e.g., absolutely no characters like ا, ب, پ, ت, ٹ, etc.).
   - Even if the merchant's message was transcribed in Urdu characters or uses Urdu vocabulary, ALWAYS write your response in Devanagari Hindi (हिन्दी) or English/Hinglish.
   - The neural text-to-speech engine bulbul:v3 crashes if Perso-Arabic script is present.
5. Live Business Grounding:
   - You have access to the merchant's real live store data below. Use these real facts to answer inventory, low-stock, pricing, and order questions.
   - Never invent imaginary stock numbers when live data is provided.
6. General Purpose Intelligence:
   - You are a general-purpose shop assistant. You can handle greetings, polite chit-chat, shop advice, GST questions, supplier management, and business queries.
7. Safe Execution Boundary:
   - If the merchant confirms or asks to approve a proposal, only acknowledge execution when an active proposal is confirmed in context. Never pretend to make payments or place unauthorized orders.
"""


class VoiceMunimAgent:
    """General-purpose conversational voice assistant for merchants."""

    def __init__(
        self,
        *,
        llm_provider: Any | None = None,
        session_factory: Any | None = None,
        workflow_runtime: Any | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.session_factory = session_factory
        self.workflow_runtime = workflow_runtime

    @property
    def runtime(self) -> Any | None:
        if callable(self.workflow_runtime):
            return self.workflow_runtime()
        return self.workflow_runtime

    async def fetch_business_context(self, merchant_id: UUID) -> dict[str, Any]:
        """Fetches live shop data to ground the voice assistant in real merchant facts."""
        context = {
            "merchant_name": "Merchant",
            "currency": "INR",
            "low_stock_items": [],
            "total_products": 0,
            "pending_approvals": 0,
            "today_sales_amount": 0.0,
            "expected_settlement": 0.0,
            "bank_name": "HDFC Bank",
            "account_ending": "4921",
            "gstin": None,
        }
        if not self.session_factory:
            return context

        try:
            from app.agents.munim_context import MunimContextService

            async with self.session_factory() as db:
                service = MunimContextService(db)
                data = await service.get_business_context(merchant_id)
                context["merchant_name"] = data.get("business_name", "Merchant")
                context["currency"] = data.get("currency", "INR")
                context["total_products"] = data.get("total_products", 0)
                context["pending_approvals"] = len(data.get("pending_approvals", []))
                context["today_sales_amount"] = data.get("today_sales_amount", 0.0)
                context["expected_settlement"] = data.get("expected_settlement", 0.0)
                context["bank_name"] = data.get("bank_name", "HDFC Bank")
                context["account_ending"] = data.get("account_ending", "4921")
                context["gstin"] = data.get("gstin")
                context["low_stock_items"] = [
                    f"{item['name']} ({item['quantity_on_hand']} {item['unit']} on hand, reorder at {item['reorder_point']} {item['unit']})"
                    for item in data.get("low_stock_items", [])
                ]
        except Exception as exc:
            logger.warning("voice_munim_context_fetch_failed", error=str(exc))

        return context

    async def handle(self, session: VoiceSession, intent: VoiceIntent) -> str:
        """Processes a transcribed merchant utterance and returns spoken text."""
        raw_text = sanitize_urdu_to_hindi(intent.raw_text.strip())
        if raw_text:
            session.add_user_message(raw_text)

        # -------------------------------------------------------------
        # 1. Deterministic Proposal Approval / Modification / Rejection
        # -------------------------------------------------------------
        if intent.intent in {
            VoiceIntentType.APPROVE_ACTIVE_PROPOSAL,
            VoiceIntentType.MODIFY_ACTIVE_PROPOSAL,
            VoiceIntentType.REJECT_ACTIVE_PROPOSAL,
        }:
            if (
                session.active_request_id
                and session.active_proposal_id
                and session.approval_token
                and self.runtime is not None
            ):
                action = {
                    VoiceIntentType.APPROVE_ACTIVE_PROPOSAL: ApprovalStatus.APPROVED,
                    VoiceIntentType.MODIFY_ACTIVE_PROPOSAL: ApprovalStatus.MODIFIED,
                    VoiceIntentType.REJECT_ACTIVE_PROPOSAL: ApprovalStatus.REJECTED,
                }[intent.intent]
                await self.runtime.resume(
                    merchant_id=session.merchant_id,
                    request_id=session.active_request_id,
                    action=action,
                    approval_token=session.approval_token,
                    quantity=float(intent.quantity) if intent.quantity else None,
                    user_id=session.user_id,
                    expected_proposal_id=session.active_proposal_id,
                )
                if action == ApprovalStatus.APPROVED:
                    reply = get_voice_message("proposal_approved", session.language_code)
                elif action == ApprovalStatus.MODIFIED:
                    reply = get_voice_message("proposal_modified", session.language_code)
                else:
                    reply = get_voice_message("proposal_rejected", session.language_code)
                session.add_assistant_message(reply)
                return reply
            else:
                reply = get_voice_message("no_active_proposal", session.language_code)
                session.add_assistant_message(reply)
                return reply

        # -------------------------------------------------------------
        # 2. Fetch Real Merchant Business Grounding Data
        # -------------------------------------------------------------
        context = await self.fetch_business_context(session.merchant_id)

        # -------------------------------------------------------------
        # 3. LLM Conversational Generation (General-Purpose Voice Agent)
        # -------------------------------------------------------------
        has_llm = self.llm_provider is not None and not isinstance(
            self.llm_provider, DisabledLLMProvider
        )
        if has_llm:
            try:
                system_prompt = self._build_system_prompt(session, context, intent)
                messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

                # Include past conversation turns from this voice session
                # (excluding the latest user message which will be appended)
                for msg in session.history[:-1]:
                    if msg.get("role") in {"user", "assistant"} and msg.get("content"):
                        messages.append({"role": msg["role"], "content": msg["content"]})

                messages.append({"role": "user", "content": raw_text or "Namaste"})

                # Run LLM with a 9-second timeout to maintain real-time responsiveness
                response_text = await asyncio.wait_for(
                    self.llm_provider.generate(messages), timeout=9.0
                )
                cleaned = clean_text_for_natural_voice(response_text)
                if cleaned:
                    session.add_assistant_message(cleaned)
                    return cleaned
            except Exception as exc:
                logger.warning("voice_munim_llm_generation_failed", error=str(exc))

        # -------------------------------------------------------------
        # 4. Intelligent Deterministic Fallback Engine
        # -------------------------------------------------------------
        fallback = self._deterministic_fallback(session, intent, context)
        cleaned = clean_text_for_natural_voice(fallback)
        session.add_assistant_message(cleaned)
        return cleaned

    def _build_system_prompt(
        self, session: VoiceSession, context: dict[str, Any], intent: VoiceIntent
    ) -> str:
        low_items_str = (
            ", ".join(context["low_stock_items"])
            if context["low_stock_items"]
            else "None (all items healthy)"
        )
        return (
            f"{VOICE_MUNIM_SYSTEM_PROMPT}\n\n"
            f"MERCHANT LIVE SHOP CONTEXT:\n"
            f"- Store Name: {context['merchant_name']}\n"
            f"- Currency: {context['currency']}\n"
            f"- GSTIN: {context.get('gstin') or 'Not Registered'}\n"
            f"- Today's Sales: ₹{context.get('today_sales_amount', 0.0):,.2f}\n"
            f"- Expected Settlement: ₹{context.get('expected_settlement', 0.0):,.2f} into {context.get('bank_name', 'HDFC Bank')} (ending {context.get('account_ending', '4921')})\n"
            f"- Total Catalog Items: {context['total_products']}\n"
            f"- Low Stock Products: {low_items_str}\n"
            f"- Pending Purchase Approvals: {context['pending_approvals']}\n"
            f"- Active Session Proposal: {'Yes' if session.active_proposal_id else 'No'}\n"
            f"- Session Language Preference: {session.language_code}\n"
            f"- Detected Intent: {intent.intent}\n"
        )

    def _deterministic_fallback(
        self, session: VoiceSession, intent: VoiceIntent, context: dict[str, Any]
    ) -> str:
        lang = session.language_code
        if intent.intent == VoiceIntentType.GREETING:
            return get_voice_message("greeting", lang)

        if intent.intent == VoiceIntentType.CAPABILITIES:
            return get_voice_message("capabilities", lang)

        if intent.intent == VoiceIntentType.QUERY_INVENTORY:
            if context["low_stock_items"]:
                sample = ", ".join(context["low_stock_items"][:2])
                if lang.startswith("hi"):
                    return f"आपकी दुकान में {sample} का स्टॉक कम है। क्या आप इनका रीऑर्डर करना चाहते हैं?"
                elif lang.startswith("gu"):
                    return f"તમારી દુકાનમાં {sample} નો સ્ટોક ઓછો છે. શું તમે ઓર્ડર કરવા માંગો છો?"
                elif lang.startswith("bn"):
                    return f"আপনার দোকানে {sample} এর স্টক কম আছে। আপনি কি অর্ডার করতে চান?"
                return f"In your store, {sample} is currently low on stock. Would you like to place a reorder?"
            return get_voice_message("inventory_all_good", lang)

        if intent.intent == VoiceIntentType.QUERY_PROPOSALS:
            if context["pending_approvals"] > 0:
                count = context["pending_approvals"]
                if lang.startswith("hi"):
                    return f"आपके पास {count} खरीद प्रस्ताव अप्रूवल के लिए पेंडिंग हैं।"
                elif lang.startswith("gu"):
                    return f"તમારી પાસે {count} ખરીદ દરખાસ્તો મંજૂરી માટે બાકી છે."
                elif lang.startswith("bn"):
                    return f"আপনার কাছে {count} টি ক্রয় প্রস্তাব অনুমোদনের অপেক্ষায় রয়েছে।"
                return f"You have {count} purchase proposals awaiting your approval."
            return get_voice_message("no_pending_proposals", lang)

        if intent.intent == VoiceIntentType.REQUEST_PURCHASE:
            return get_voice_message("purchase_request", lang)

        if intent.intent == VoiceIntentType.REPORT_LOW_STOCK:
            return get_voice_message("low_stock", lang)

        return get_voice_message("general_help", lang)
