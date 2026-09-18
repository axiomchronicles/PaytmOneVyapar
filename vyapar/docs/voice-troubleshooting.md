# Voice troubleshooting

The backend reads only `SARVAM_API_KEY` through `Settings`, strips accidental surrounding quotes/whitespace, and passes it to `sarvamai` as `api_subscription_key`. SDK 0.1.33 sends `api-subscription-key` to `https://api.sarvam.ai` / `wss://api.sarvam.ai`.

Startup logs only `credential_present`, `credential_length`, and `credential_source`; the key itself is never logged. Provider authentication failures become `SARVAM_AUTHENTICATION_FAILED` with “Voice service is temporarily unavailable.” Secure logs retain provider/error type without credentials.

Expected protocol:

```text
PCM16 16 kHz microphone
 -> TRANSCRIPT_PARTIAL / TRANSCRIPT_FINAL
 -> ACTION
 -> workflow response
 -> RESPONSE_TEXT
 -> AUDIO_START {codec,sample_rate,channels}
 -> binary audio chunks
 -> AUDIO_END
```

For continuous Flutter playback configure `SARVAM_TTS_CODEC=linear16`. The client prebuffers about 300 ms and continuously feeds one PCM player. It never starts a player per chunk. Barge-in sends `interrupt`, flushes buffered playback, and resumes listening.

Diagnostic commands:

```bash
cd backend
uv run python scripts/test_sarvam_voice.py --lang hindi
uv run pytest tests/voice
```

If the provider reports `invalid_subscription_key`, confirm that the deployment secret named `SARVAM_API_KEY` contains the active Sarvam subscription key with no quotes/newline and restart the API. Do not put the key in Flutter.
