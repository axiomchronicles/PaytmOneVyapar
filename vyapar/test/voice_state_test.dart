import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/features/voice/models/voice_models.dart';

void main() {
  test(
    'voice session response separates input audio from provider availability',
    () {
      final session = VoiceSessionInfo.fromJson({
        'session_id': 'session-id',
        'stream_url': '/api/v1/voice/sessions/session-id/stream',
        'provider_available': true,
        'audio': {'encoding': 'linear16', 'sample_rate': 16000, 'channels': 1},
      });

      expect(session.providerAvailable, isTrue);
      expect(session.inputEncoding, 'linear16');
      expect(session.inputSampleRate, 16000);
    },
  );

  test('voice state retains transcript through thinking and speaking', () {
    const initial = VoiceState(phase: VoicePhase.listening);
    final thinking = initial.copyWith(
      phase: VoicePhase.thinking,
      transcript: 'stock kitna hai',
    );
    final speaking = thinking.copyWith(
      phase: VoicePhase.speaking,
      response: 'Checking your inventory.',
    );

    expect(speaking.transcript, 'stock kitna hai');
    expect(speaking.response, 'Checking your inventory.');
  });
}
