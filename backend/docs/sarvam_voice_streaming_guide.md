# Sarvam AI Voice Agent Architecture & Natural Voice Streaming Guide

## Executive Summary

This document provides a comprehensive technical analysis of the **PaytmOneVyapar / Vyapaar Commander** voice agent integration with **Sarvam AI**, focusing on the **Ritu** female voice persona (`bulbul:v3`). It diagnoses the root causes of the *"voice buffering after each word / robotic stuttering"* issue, details official Sarvam AI documentation and best practices, and explains the engineering architecture required to achieve **continuous, studio-quality, natural human-like speech**.

---

## 1. Codebase Architecture & Voice Flow Overview

The PaytmOneVyapar backend is an autonomous B2B replenishment and voice-assisted negotiation engine built on **FastAPI**, **LangGraph**, and **A2A (Agent-to-Agent)** protocol:

```
[Merchant / User Voice]
        │ (Audio Stream: linear16 PCM, 16kHz)
        ▼
[FastAPI WebSocket Endpoint: /api/v1/voice/sessions/{session_id}/stream]
        │
        ▼
[VoicePipeline (app/channels/voice/pipeline.py)]
        │
        ├──► 1. STT Stream: SarvamVoiceProvider.transcribe() (saaras:v4 realtime)
        │         └── Emits TRANSCRIPT_PARTIAL and TRANSCRIPT_FINAL
        │
        ├──► 2. Intent Extraction: extract_voice_intent()
        │         └── Detects quantities, SKUs, and Indian language action verbs
        │
        ├──► 3. Workflow Execution: LangGraph WorkflowRuntime
        │         └── Approves, modifies, or rejects purchase proposals
        │
        ├──► 4. Localized Response: get_voice_message() (app/channels/voice/i18n.py)
        │         └── Generates polite, natural female merchant assistant phrasing
        │
        └──► 5. TTS Stream: SarvamVoiceProvider.synthesize() (bulbul:v3, speaker: ritu)
                  └── Emits AUDIO_START, binary audio chunks, and AUDIO_END
```

### Core Voice Modules
1. **`app/channels/voice/sarvam.py`**: Wraps Sarvam AI SDK (`AsyncSarvamAI`) for real-time STT (`saaras:v4`) and neural streaming TTS (`bulbul:v3`).
2. **`app/channels/voice/pipeline.py`**: Coordinates the STT-to-intent-to-action-to-TTS loop with barge-in interruption handling.
3. **`app/channels/voice/protocol.py`**: Defines standard WebSocket control and audio frame schemas (`VoiceEventType.AUDIO_START`, `AUDIO`, `AUDIO_END`, `ACTION`).
4. **`app/channels/voice/i18n.py`**: Multi-lingual localized responses across 7 Indian languages (Hindi, Gujarati, Bengali, Bhojpuri, Tamil, Telugu, Marathi).
5. **`app/channels/voice/session.py`**: In-memory state tracking linked to PostgreSQL voice session audit logs.
6. **`scripts/test_sarvam_voice.py`**: Interactive CLI testing suite simulating STT input, proposal resolution, and TTS playback.

---

## 2. Root Cause Analysis: Why Voice Was Buffering & Sounding Robotic

When users experience the voice *"buffering after each word/chunk"* and sounding *"robotic and unnatural"*, the issue stems from a combination of **audio streaming transport physics**, **TTS neural model parameterization**, and **client playback architecture**:

### Root Cause 1: Playing Audio Chunks Independently (Buffer Underrun)
* **The Problem**: In streaming TTS, Sarvam's WebSocket yields small audio chunks (often 100ms – 300ms of audio each) as they are synthesized. If a client player receives chunk $N$ and immediately plays it via `new Audio(blob).play()` or naive player calls, chunk $N$ completes playback **before chunk $N+1$ finishes downloading over the network**.
* **The Symptom**: The audio device stutters, starves, and stops. On Bluetooth earphones/earbuds, the Bluetooth A2DP audio link enters a low-power pause state between each chunk, causing audible clicks, pops, latency catch-up, and a harsh "machine-gun" buffering cadence after every few words.

### Root Cause 2: MP3 Frame Boundary & Bit-Reservoir Misalignment
* **The Problem**: MP3 is a lossy compressed format that utilizes a **bit reservoir** (borrowing bits from previous frames). Individual WebSocket chunks do **not** align to standalone MP3 frame headers. 
* **The Symptom**: Calling browser `decodeAudioData()` on isolated incoming MP3 chunks fails or inserts zero-padding/silence at the boundaries. This creates metallic distortion, clicks, and a robotic tone.

### Root Cause 3: Suboptimal Neural Prosody Parameters in `bulbul:v3`
* **The Problem**: In `bulbul:v3`, expressiveness and natural human inflection are controlled by the `temperature` parameter (default 0.6, range 0.01 – 2.0). If `temperature` is not passed, or if legacy `pitch` / `loudness` parameters are passed (which `bulbul:v3` does not support), the model defaults to a flat, monotonous, synthesized pitch contour.
* **The Symptom**: The voice sounds robotic, devoid of emotional warmth and natural sentence pitch rise-and-fall.

### Root Cause 4: Insufficient Sentence Context (`min_buffer_size` & Flush)
* **The Problem**: Sarvam's `bulbul:v3` uses an LLM-based text analysis layer to understand sentence grammar, breath pauses, and emphasis. If text is flushed immediately or chunked into tiny 2–3 word pieces via small buffer sizes, the LLM cannot predict the full sentence prosody.
* **The Symptom**: Words sound disconnected, as if individual syllables were stitched together rather than spoken in a single human breath.

### Root Cause 5: Punctuation and Phrasing Mismatch
* **The Problem**: Rigid punctuation like double dashes (`--`), semicolons (`;`), or excessive full stops (`.`) force the neural engine into unnatural prolonged silences. In Indian languages, long sentences without natural clause commas (`,`) force the engine to speak without taking natural breath pauses.

---

## 3. Sarvam AI Documentation: Official Best Practices

Based on official Sarvam AI engineering guidelines:

### 1. Speaker Selection: Why `ritu`
* **Voice Profile**: `ritu` is Sarvam's flagship female conversational speaker in `bulbul:v3`.
* **Characteristics**: Studio-recorded, expressive prosody, energetic, highly capable of code-mixed Indian English and regional native languages.
* **Supported Languages**: Hindi, Gujarati, Bengali, Tamil, Telugu, Marathi, Kannada, Malayalam, Odia, Punjabi, and Indian English.

### 2. Bulbul v3 Parameters
| Parameter | Optimal Value | Function |
| :--- | :--- | :--- |
| `model` | `"bulbul:v3"` | State-of-the-art multilingual neural TTS engine |
| `speaker` | `"ritu"` | Expressive, warm female assistant persona |
| `temperature` | `0.6` | Natural human expressiveness and prosody (range: 0.01 – 2.0) |
| `pace` | `1.0` | Natural conversational speed (range: 0.5 – 2.0) |
| `speech_sample_rate`| `24000` | Native 24 kHz studio sample rate |
| `output_audio_codec`| `"mp3"` or `"linear16"` | Streaming codec |
| `output_audio_bitrate`| `"192k"` | Maximum audio fidelity, zero compression artifacts |
| `enable_preprocessing`| `true` | Normalizes numerals, dates, prices, and Hinglish |
| `min_buffer_size` | `60` | Ensures adequate sentence context before synthesis |
| `max_chunk_length` | `200` | Optimal natural clause length |

*(Note: In `bulbul:v3`, `pitch` and `loudness` are deprecated/unsupported; do not send them).*

### 3. Transport Strategy (WebSocket vs. HTTP Stream vs. REST)
* **WebSocket Streaming (`wss://api.sarvam.ai/text-to-speech/ws`)**: Best for low-latency interactive voice agents where text is generated dynamically.
* **HTTP Streaming (`POST /text-to-speech/stream`)**: Direct binary stream over HTTP. Eliminates WebSocket handshake overhead for server-to-server forwarding.
* **Keep-Alive**: WebSockets close after 60 seconds of idle time. Production clients must send a `{"type": "ping"}` heartbeat every 20–30 seconds during idle conversation periods.

---

## 4. How to Play Streaming Sound Naturally (Zero Buffering & Zero Stutter)

To eliminate the "buffering after each word / earbuds stutter" issue, clients must use **Jitter Buffering** and **Audio Timeline Scheduling**:

### Architecture: The Web Audio API Jitter Buffer
Instead of playing each chunk as an isolated audio element, incoming audio chunks are queued onto an uninterrupted audio timeline using the browser's `AudioContext.currentTime`:

```
Incoming WebSocket Chunks:  [Chunk 1] ───► [Chunk 2] ───► [Chunk 3]
                                │              │              │
                     (Pre-roll Buffer: 150ms - 200ms)
                                │              │              │
AudioContext Timeline:      [════ Chunk 1 ════][════ Chunk 2 ════][════ Chunk 3 ════]
                            ▲                  ▲                  ▲
                      currentTime        currentTime+d1     currentTime+d1+d2
                      (Continuous, uninterrupted, seamless playback directly to earbuds)
```

### Key Engineering Steps:
1. **Pre-roll Delay**: When `AUDIO_START` arrives, accumulate 150ms – 250ms of audio before starting the playback timeline. This absorbs network latency variance (jitter).
2. **Scheduled Playback**: Schedule chunk $K+1$ to start exactly at `startTime(K) + duration(K)`. The audio hardware never runs out of samples, eliminating the Bluetooth earbud pause state.
3. **Audio Framing Protocol**: The server emits `AUDIO_START` and `AUDIO_END` events so the client knows when to initialize the queue and when the utterance has concluded.

---

## 5. Implementation Reference

A complete working reference player is provided in [`scripts/voice_streaming_player_demo.html`](file:///Users/kuroyami/ProjectPaytmOneVyapar/backend/scripts/voice_streaming_player_demo.html).
