#!/usr/bin/env python3
"""Interactive Multilingual Test and Simulation Suite for the Sarvam AI Voice Agent.

Optimized for smooth, natural, continuous female voice synthesis without robotic pauses.

Supports:
- Hindi (hi-IN) - Female (कर रही हूँ, जोड़ सकी)
- Gujarati (gu-IN) - Female (કરી રહી છું, જોડી શકી નથી)
- Bengali (bn-IN) - Female (তৈরি করছি)
- Bhojpuri (bho-IN) - Female (बनावत बानी)
- Tamil (ta-IN) - Female (தயாரிக்கிறேன்)
- Telugu (te-IN) - Female (చేస్తున్నాను)
- Marathi (mr-IN) - Female (तयार करत आहे, करू शकले नाही)

Demonstrates:
1. Native language speech input transcription (STT simulation).
2. Domain-aware intent extraction with regional numerals, units, and action verbs.
3. LangGraph workflow replenishment execution.
4. Response synthesis in native Indian languages using Sarvam AI bulbul:v3 (cloud)
   or local native Indian female speech engines (Lekha, Piya, Vani, Geeta via /usr/bin/afplay).
"""

import argparse
import asyncio
import re
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.graph import build_purchase_graph
from app.agents.runtime import WorkflowRuntime
from app.agents.services import (
    InMemoryApprovalAuthority,
    SecureMemoryTransactionExecutor,
    WorkflowServices,
)
from app.channels.voice.agent import VoiceMunimAgent
from app.channels.voice.i18n import get_voice_message
from app.channels.voice.pipeline import VoicePipeline
from app.channels.voice.protocol import VoiceEvent, VoiceEventType, VoiceIntentType
from app.channels.voice.provider import VoiceProvider
from app.channels.voice.sarvam import SarvamVoiceProvider
from app.channels.voice.session import VoiceSession
from app.core.config import get_settings
from app.domain.enums import ApprovalStatus
from app.integrations.llm import build_llm_provider
from app.integrations.suppliers.mock_supplier import MockSupplierAdapter
from app.ml.demand.baseline import BaselineForecaster

LANGUAGE_CONFIGS: dict[str, dict[str, str]] = {
    "hindi": {
        "code": "hi-IN",
        "name": "Hindi (हिंदी)",
        "mac_voice": "Lekha",
        "sarvam_speaker": "ritu",
        "low_stock_input": "भैया कोल्ड ड्रिंक खत्म हो रही है",
        "purchase_input": "तीन पेटी कोल्ड ड्रिंक और मंगवा दो",
        "approve_input": "हाँ कन्फर्म कर दो",
    },
    "gujarati": {
        "code": "gu-IN",
        "name": "Gujarati (ગુજરાતી)",
        "mac_voice": "Lekha",
        "sarvam_speaker": "ritu",
        "low_stock_input": "ભાઈ કોલ્ડ ડ્રિંક ઓછો થઈ ગયો છે",
        "purchase_input": "ત્રણ પેટી કોલ્ડ ડ્રિંક મંગાવી દો",
        "approve_input": "હા કન્ફર્મ કરી દો",
    },
    "bengali": {
        "code": "bn-IN",
        "name": "Bengali (বাংলা)",
        "mac_voice": "Piya",
        "sarvam_speaker": "ritu",
        "low_stock_input": "দাদা কোল্ড ড্রিঙ্ক শেষ হয়ে গেছে",
        "purchase_input": "তিন পেটি কোল্ড ড্রিঙ্ক আনিয়ে দিন",
        "approve_input": "হ্যাঁ কনফার্ম করে দিন",
    },
    "bhojpuri": {
        "code": "bho-IN",
        "name": "Bhojpuri (भोजपुरी)",
        "mac_voice": "Lekha",
        "sarvam_speaker": "ritu",
        "low_stock_input": "भइया कोल्ड ड्रिंक सिरा गइल बा",
        "purchase_input": "तीन पेटी कोल्ड ड्रिंक मँगवा दीं",
        "approve_input": "हाँ कन्फर्म कs दीं",
    },
    "tamil": {
        "code": "ta-IN",
        "name": "Tamil (தமிழ்)",
        "mac_voice": "Vani",
        "sarvam_speaker": "ritu",
        "low_stock_input": "அண்ணா கோல்ட் டிரிங்க் தீர்ந்துவிட்டது",
        "purchase_input": "மூன்று பெட்டி கோல்ட் டிரிங்க் ஆர்டர் பண்ணுங்க",
        "approve_input": "ஆமாம் உறுதி பண்ணுங்க",
    },
    "telugu": {
        "code": "te-IN",
        "name": "Telugu (తెలుగు)",
        "mac_voice": "Geeta",
        "sarvam_speaker": "ritu",
        "low_stock_input": "అన్నా కోల్డ్ డ్రింక్ అయిపోయింది",
        "purchase_input": "మూడు పెట్టెలు కోల్డ్ డ్రింక్ ఆర్డర్ చేయండి",
        "approve_input": "అవును కన్ఫర్మ్ చేయండి",
    },
    "marathi": {
        "code": "mr-IN",
        "name": "Marathi (मराठी)",
        "mac_voice": "Lekha",
        "sarvam_speaker": "ritu",
        "low_stock_input": "दादा कोल्ड ड्रिंक संपले आहे",
        "purchase_input": "तीन पेट्या कोल्ड ड्रिंक मागवून घ्या",
        "approve_input": "हो करा कन्फर्म",
    },
}


def gujarati_to_phonetic_devanagari(text: str) -> str:
    """Transliterate Gujarati Unicode script to Devanagari for smooth macOS Lekha TTS playback.

    macOS does not have a native Gujarati voice engine. Passing raw Gujarati Unicode to
    Lekha (Hindi engine) causes it to skip glyphs, resulting in broken/robotic speech.
    Since Gujarati phonology maps 1:1 to Devanagari (offset 0x0180), this allows Lekha
    to speak fluid, natural Gujarati.
    """
    res = []
    for ch in text:
        code = ord(ch)
        if 0x0A81 <= code <= 0x0AF9:
            res.append(chr(code - 0x0180))
        else:
            res.append(ch)
    return "".join(res)


def clean_text_for_smooth_speech(text: str) -> str:
    """Normalize pauses and punctuation so the TTS engine speaks in a continuous, natural flow."""
    # Replace multiple dots/dashes that cause unnatural pauses
    cleaned = re.sub(r"\.{2,}", ".", text)
    cleaned = re.sub(r"-{2,}", " ", cleaned)
    # Remove awkward symbols that make TTS halt
    cleaned = cleaned.replace(";", ",").replace(":", ",")
    return cleaned.strip()


class SmoothMacVoiceProvider(VoiceProvider):
    """Voice provider that synthesizes smooth, natural, continuous female speech on macOS."""

    def __init__(
        self,
        voice_name: str = "Lekha",
        simulated_transcript: str = "",
        speech_rate: int = 175,
        is_gujarati: bool = False,
    ) -> None:
        self.voice_name = voice_name
        self.simulated_transcript = simulated_transcript
        self.speech_rate = speech_rate
        self.is_gujarati = is_gujarati

    async def transcribe(
        self,
        audio: AsyncIterator[bytes],
        *,
        language_code: str,
        sample_rate: int = 16000,
        encoding: str = "linear16",
    ) -> AsyncIterator[VoiceEvent]:
        async for _ in audio:
            pass
        yield VoiceEvent(
            type=VoiceEventType.TRANSCRIPT_FINAL,
            text=self.simulated_transcript,
            language_code=language_code,
            metadata={"utterance_index": 0},
        )

    async def synthesize(self, text: str, *, language_code: str) -> AsyncIterator[VoiceEvent]:
        temp_dir = Path(tempfile.gettempdir())
        aiff_path = temp_dir / f"voice_smooth_{uuid4().hex[:8]}.aiff"

        # Prepare smoothed text
        speech_text = clean_text_for_smooth_speech(text)
        if self.is_gujarati:
            speech_text = gujarati_to_phonetic_devanagari(speech_text)

        # Use natural speech rate (-r 175) to prevent word-by-word buffering pauses
        cmd = ["/usr/bin/say", "-r", str(self.speech_rate), "-o", str(aiff_path)]
        if self.voice_name:
            cmd.extend(["-v", self.voice_name])
        cmd.append(speech_text)

        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.communicate()

        if aiff_path.exists():
            # Play native high-fidelity AIFF directly (avoids resampling aliasing/robotic distortion)
            audio_bytes = await asyncio.to_thread(aiff_path.read_bytes)
            aiff_path.unlink(missing_ok=True)

            yield VoiceEvent(
                type=VoiceEventType.AUDIO,
                audio=audio_bytes,
                audio_content_type="audio/aiff",
                language_code=language_code,
            )


class SarvamSimulatedTranscribeProvider(VoiceProvider):
    """Wraps SarvamVoiceProvider for TTS while injecting simulated STT transcript."""

    def __init__(self, sarvam: SarvamVoiceProvider, simulated_transcript: str = "") -> None:
        self.sarvam = sarvam
        self.simulated_transcript = simulated_transcript

    async def transcribe(
        self,
        audio: AsyncIterator[bytes],
        *,
        language_code: str,
        sample_rate: int = 16000,
        encoding: str = "linear16",
    ) -> AsyncIterator[VoiceEvent]:
        async for _ in audio:
            pass
        yield VoiceEvent(
            type=VoiceEventType.TRANSCRIPT_FINAL,
            text=self.simulated_transcript,
            language_code=language_code,
            metadata={"utterance_index": 0},
        )

    async def synthesize(self, text: str, *, language_code: str) -> AsyncIterator[VoiceEvent]:
        async for event in self.sarvam.synthesize(text, language_code=language_code):
            yield event


def play_audio(audio_bytes: bytes, suffix: str = ".aiff") -> None:
    """Play audio bytes smoothly using macOS afplay."""
    if not audio_bytes:
        return
    temp_file = Path(tempfile.gettempdir()) / f"vyapaar_voice_play_{uuid4().hex[:8]}{suffix}"
    try:
        temp_file.write_bytes(audio_bytes)
        print(f"   🔊 Speaking ({len(audio_bytes)} bytes) via /usr/bin/afplay...")
        subprocess.run(["/usr/bin/afplay", str(temp_file)], check=True)  # noqa: S603
    except Exception as exc:
        print(f"   ⚠️ Audio playback notice: {exc}")
    finally:
        temp_file.unlink(missing_ok=True)


async def dummy_audio_stream() -> AsyncIterator[bytes]:
    """Generates dummy linear16 PCM audio bytes for pipeline input."""
    for _ in range(3):
        yield b"\x00" * 3200
        await asyncio.sleep(0.01)


async def run_scenario_for_language(
    lang_key: str,
    raw_sarvam_provider: SarvamVoiceProvider | None = None,
    use_sarvam: bool = False,
) -> None:
    config = LANGUAGE_CONFIGS[lang_key]
    lang_code = config["code"]
    lang_name = config["name"]
    mac_voice = config["mac_voice"]
    is_guj = lang_key == "gujarati"

    print("\n" + "=" * 70)
    print(f"🗣️  TESTING LANGUAGE: {lang_name.upper()} [{lang_code}]")
    print(
        f"• Voice Persona: Female Assistant ({'Sarvam ritu' if use_sarvam else f'macOS {mac_voice}'})"
    )
    print(
        f"• Speech Engine: {'Sarvam AI bulbul:v3 Neural TTS' if use_sarvam else 'macOS High-Fidelity Speech Engine'}"
    )
    print("=" * 70)

    # Initialize LangGraph runtime dependencies
    secret = "demo-approval-secret-with-32-characters"
    supplier = MockSupplierAdapter(signing_secret="demo-a2a-secret-with-32-characters")
    approvals = InMemoryApprovalAuthority(secret)
    services = WorkflowServices(
        forecast_model=BaselineForecaster(),
        suppliers=[supplier],
        approval_authority=approvals,
        transaction_executor=SecureMemoryTransactionExecutor(approvals, [supplier]),
    )
    from langgraph.checkpoint.memory import InMemorySaver

    runtime = WorkflowRuntime(
        build_purchase_graph(services, checkpointer=InMemorySaver()), approvals
    )

    merchant_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    user_id = UUID("99999999-9999-4999-8999-999999999999")

    llm = build_llm_provider(settings)
    munim_agent = VoiceMunimAgent(llm_provider=llm, workflow_runtime=runtime)
    handle_voice_action = munim_agent.handle

    # -------------------------------------------------------------
    # Scenario 1: Report Low Stock in Native Language
    # -------------------------------------------------------------
    spoken_1 = config["low_stock_input"]
    print(f"\n[1. Low Stock Alert] Merchant says: '{spoken_1}'")

    if use_sarvam and raw_sarvam_provider:
        prov_1 = SarvamSimulatedTranscribeProvider(
            raw_sarvam_provider, simulated_transcript=spoken_1
        )
    else:
        prov_1 = SmoothMacVoiceProvider(
            voice_name=mac_voice,
            simulated_transcript=spoken_1,
            speech_rate=175,
            is_gujarati=is_guj,
        )

    pipe_1 = VoicePipeline(prov_1, handle_voice_action)
    sess_1 = VoiceSession(merchant_id=merchant_id, user_id=user_id, language_code=lang_code)

    chunks_1: list[bytes] = []
    async for event in pipe_1.run(sess_1, dummy_audio_stream()):
        if event.type == VoiceEventType.ACTION:
            print(
                f"   🧠 Detected Intent: {event.metadata.get('intent')} (sku={event.metadata.get('sku_hint')})"
            )
        elif event.type == VoiceEventType.RESPONSE_TEXT:
            print(f'   🤖 Female Agent Speaks ({lang_name}): "{event.text}"')
        elif event.type == VoiceEventType.AUDIO and event.audio:
            chunks_1.append(event.audio)

    play_audio(b"".join(chunks_1), suffix=".mp3" if use_sarvam else ".aiff")

    # -------------------------------------------------------------
    # Scenario 2: Proposal Voice Approval in Native Language
    # -------------------------------------------------------------
    initial_wf = {
        "merchant_id": str(merchant_id),
        "store_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "request_id": f"req-voice-{lang_key}-001",
        "sku": "COLD-COLA-300",
        "required_quantity": 0,
        "unit": "crate",
        "target_price": 450,
        "max_price": 480,
        "spending_limit": 50000,
        "delivery_requirement": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "inventory_snapshot": {
            "quantity_on_hand": 3,
            "reorder_point": 8,
            "safety_stock": 2,
            "captured_at": datetime.now(UTC).isoformat(),
        },
        "sales_history": [
            {
                "date": (datetime.now(UTC) - timedelta(days=d)).isoformat(),
                "sales": 7 if d <= 7 else 4,
                "inventory": 20,
                "price": 600,
            }
            for d in range(28, 0, -1)
        ],
        "trace_id": f"trace-{lang_key}",
        "proposal_revision": 1,
        "attempted_supplier_ids": [],
    }
    waiting_state = await runtime.start(initial_wf)
    print(
        f"\n[2. Voice Approval] Proposed 6 crates @ ₹{waiting_state['proposal']['unit_price']}/crate"
    )

    spoken_2 = config["approve_input"]
    print(f"   Merchant says: '{spoken_2}'")

    if use_sarvam and raw_sarvam_provider:
        prov_2 = SarvamSimulatedTranscribeProvider(
            raw_sarvam_provider, simulated_transcript=spoken_2
        )
    else:
        prov_2 = SmoothMacVoiceProvider(
            voice_name=mac_voice,
            simulated_transcript=spoken_2,
            speech_rate=175,
            is_gujarati=is_guj,
        )

    pipe_2 = VoicePipeline(prov_2, handle_voice_action)
    sess_2 = VoiceSession(
        merchant_id=merchant_id,
        user_id=user_id,
        language_code=lang_code,
        active_proposal_id=UUID(waiting_state["proposal"]["proposal_id"]),
        active_request_id=initial_wf["request_id"],
        approval_token=waiting_state["approval_token"],
    )

    chunks_2: list[bytes] = []
    async for event in pipe_2.run(sess_2, dummy_audio_stream()):
        if event.type == VoiceEventType.ACTION:
            print(
                f"   🧠 Detected Intent: {event.metadata.get('intent')} (explicit={event.metadata.get('explicit_confirmation')})"
            )
        elif event.type == VoiceEventType.RESPONSE_TEXT:
            print(f'   🤖 Female Agent Speaks ({lang_name}): "{event.text}"')
        elif event.type == VoiceEventType.AUDIO and event.audio:
            chunks_2.append(event.audio)

    play_audio(b"".join(chunks_2), suffix=".mp3" if use_sarvam else ".aiff")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test Multilingual Sarvam Voice Agent")
    parser.add_argument(
        "--lang",
        choices=["hindi", "gujarati", "bengali", "bhojpuri", "tamil", "telugu", "marathi", "all"],
        default="hindi",
        help="Language to test (default: hindi, or 'all' to cycle through all 7 languages)",
    )
    parser.add_argument("--api-key", help="Sarvam AI API Subscription Key (overrides .env)")
    parser.add_argument(
        "--speaker", default="ritu", help="Sarvam TTS Speaker (default: ritu, female voice)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.6,
        help="bulbul:v3 expressiveness (0.01-2.0, default: 0.6)",
    )
    parser.add_argument(
        "--pace", type=float, default=1.0, help="Speech pace speed (0.5-2.0, default: 1.0)"
    )
    args = parser.parse_args()

    settings = get_settings()
    api_key = args.api_key or (
        settings.sarvam_api_key.get_secret_value() if settings.sarvam_api_key else None
    )
    is_valid_sarvam_key = bool(api_key and api_key != "change-me-temporary")

    print("=" * 70)
    print("   VYAPAAR COMMANDER - SMOOTH FEMALE VOICE AGENT SUITE")
    print("=" * 70)
    print("Voice Character: Polite Female Merchant Assistant")
    print("Languages Supported: Hindi, Gujarati, Bengali, Bhojpuri, Tamil, Telugu, Marathi")

    raw_sarvam_provider: SarvamVoiceProvider | None = None
    if is_valid_sarvam_key:
        print(
            "🔑 Sarvam credential present "
            f"(length={len(api_key)}, source={'--api-key' if args.api_key else 'SARVAM_API_KEY'}, "
            f"bulbul:v3, female speaker: {args.speaker}, temp: {args.temperature})"
        )
        raw_sarvam_provider = SarvamVoiceProvider(
            api_key=api_key,
            stt_model=settings.sarvam_stt_model,
            tts_model=settings.sarvam_tts_model,
            tts_speaker=args.speaker,
            tts_pace=args.pace,
            tts_temperature=args.temperature,
            tts_sample_rate=settings.sarvam_tts_sample_rate,
            tts_codec=settings.sarvam_tts_codec,
            tts_bitrate=settings.sarvam_tts_bitrate,
        )
    else:
        print("\nVoice unavailable: SARVAM_API_KEY is not configured with a live credential.")
        print("No simulated voice fallback was run.")
        return

    languages_to_run = list(LANGUAGE_CONFIGS.keys()) if args.lang == "all" else [args.lang]

    for lang in languages_to_run:
        await run_scenario_for_language(
            lang,
            raw_sarvam_provider=raw_sarvam_provider,
            use_sarvam=True,
        )

    print("\n" + "=" * 70)
    print("LIVE SARVAM VOICE SCENARIOS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
