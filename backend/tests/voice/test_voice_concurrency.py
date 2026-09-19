import asyncio
from uuid import uuid4

import pytest
from websockets.legacy.protocol import WebSocketCommonProtocol

from app.channels.voice.pipeline import VoicePipeline
from app.channels.voice.protocol import VoiceEvent, VoiceEventType, VoiceIntent
from app.channels.voice.provider import VoiceProvider
from app.channels.voice.session import VoiceSession


@pytest.mark.asyncio
async def test_websockets_drain_helper_handles_concurrency_without_assertion_error() -> None:
    """Verifies that concurrent drain calls do not crash with AssertionError."""
    protocol = WebSocketCommonProtocol()
    protocol.loop = asyncio.get_running_loop()
    protocol.connection_lost_waiter = protocol.loop.create_future()
    protocol._paused = True
    protocol._drain_waiter = None

    t1 = asyncio.create_task(protocol._drain_helper())
    await asyncio.sleep(0.001)
    # Without patch, calling _drain_helper again raises AssertionError
    t2 = asyncio.create_task(protocol._drain_helper())
    await asyncio.sleep(0.001)

    assert not t1.done()
    assert not t2.done()

    # Resume writing should resolve both waiters cleanly
    protocol.resume_writing()
    await asyncio.gather(t1, t2)
    assert t1.done() and t2.done()


@pytest.mark.asyncio
async def test_websockets_drain_helper_handles_connection_lost() -> None:
    """Verifies that connection loss raises ConnectionResetError on all waiters."""
    protocol = WebSocketCommonProtocol()
    protocol.loop = asyncio.get_running_loop()
    protocol.connection_lost_waiter = protocol.loop.create_future()
    protocol._paused = True
    protocol._drain_waiter = None

    t1 = asyncio.create_task(protocol._drain_helper())
    await asyncio.sleep(0.001)
    t2 = asyncio.create_task(protocol._drain_helper())
    await asyncio.sleep(0.001)

    protocol.connection_lost(ConnectionResetError("Connection lost"))
    results = await asyncio.gather(t1, t2, return_exceptions=True)
    assert all(isinstance(r, ConnectionResetError) for r in results)


class DummyVoiceProvider(VoiceProvider):
    def __init__(self, transcript: str = "namaste") -> None:
        self.transcript = transcript
        self.synthesize_called = False

    async def transcribe(
        self,
        audio,
        *,
        language_code: str,
        sample_rate: int = 16000,
        encoding: str = "linear16",
    ):
        async for _ in audio:
            pass
        yield VoiceEvent(
            type=VoiceEventType.TRANSCRIPT_FINAL,
            text=self.transcript,
            language_code=language_code,
        )

    async def synthesize(self, text: str, *, language_code: str):
        self.synthesize_called = True
        yield VoiceEvent(
            type=VoiceEventType.AUDIO,
            audio=b"\x01\x02\x03",
            language_code=language_code,
        )


@pytest.mark.asyncio
async def test_voice_pipeline_manages_session_speaking_state() -> None:
    session = VoiceSession(merchant_id=uuid4(), user_id=uuid4(), language_code="hi-IN")
    assert not session.speaking

    speaking_during_action = []

    async def dummy_action_handler(sess: VoiceSession, intent: VoiceIntent) -> str:
        speaking_during_action.append(sess.speaking)
        return "नमस्ते, मैं रितु हूँ।"

    provider = DummyVoiceProvider()
    pipeline = VoicePipeline(provider, dummy_action_handler)

    async def empty_audio():
        yield b"\x00" * 320
        return

    events = []
    async for event in pipeline.run(session, empty_audio()):
        events.append(event)

    # During action handler and synthesis, session.speaking must have been True
    assert speaking_during_action == [True]
    # After pipeline completes utterance, session.speaking must be False
    assert not session.speaking
    assert provider.synthesize_called
    event_types = [e.type for e in events]
    assert VoiceEventType.AUDIO_START in event_types
    assert VoiceEventType.AUDIO in event_types
    assert VoiceEventType.AUDIO_END in event_types


@pytest.mark.asyncio
async def test_voice_session_interrupt_clears_speaking_state() -> None:
    session = VoiceSession(merchant_id=uuid4(), user_id=uuid4(), language_code="hi-IN")
    session.speaking = True
    session.interrupt()
    assert session.interrupted is True
    assert session.speaking is False
