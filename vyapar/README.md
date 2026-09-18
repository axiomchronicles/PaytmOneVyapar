# Paytm One Vyapar Flutter client

Merchant-facing Flutter client for the FastAPI service in `../backend`.

## Run locally

Start and seed the backend using its own local-development guide, then run:

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Android emulators default to `http://10.0.2.2:8000/api/v1`; Apple and desktop targets default to `http://127.0.0.1:8000/api/v1`. Always set `API_BASE_URL` explicitly for devices and production.

The seeded backend account is documented in `../backend/README.md`. The app never embeds demo credentials.

## Voice

Microphone input is mono PCM16 at 16 kHz. Continuous TTS playback is enabled only when the backend is configured to emit raw PCM:

```bash
# backend
SARVAM_TTS_CODEC=linear16

# Flutter
flutter run \
  --dart-define=VOICE_OUTPUT_CODEC=linear16 \
  --dart-define=VOICE_OUTPUT_SAMPLE_RATE=24000
```

The backend advertises output codec/sample rate in the session and `AUDIO_START`. The client continuously prebuffers and plays `linear16`; when the backend emits MP3 it keeps transcript/control state live without misinterpreting compressed chunks as PCM.

## Verify

```bash
flutter analyze
flutter test
flutter test integration_test/auth_navigation_test.dart
flutter build apk --debug
```

Architecture and backend capability details are in:

- `docs/frontend-architecture.md`
- `docs/screen-map.md`
- `docs/backend-contract-map.md`
