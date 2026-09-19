import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/features/voice/models/voice_models.dart';
import 'package:vyapar/features/voice/presentation/voice_screen.dart';
import 'package:vyapar/features/voice/providers/voice_provider.dart';

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

  testWidgets('voice screen renders red DangerButton when Munim is speaking', (tester) async {
    final speakingState = const VoiceState(
      phase: VoicePhase.speaking,
      response: 'Haan ji, main check kar rahi hoon.',
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          voiceControllerProvider.overrideWith(() => _SpeakingVoiceController(speakingState)),
        ],
        child: const MaterialApp(
          home: VoiceScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final interruptFinder = find.byKey(const ValueKey('voice_interrupt_button'));
    expect(interruptFinder, findsOneWidget);
    expect(find.text('Interrupt Munim'), findsOneWidget);

    final button = tester.widget<DangerButton>(interruptFinder);
    expect(button.style, AppButtonStyle.danger);
  });
}

class _SpeakingVoiceController extends VoiceController {
  _SpeakingVoiceController(this._state);
  final VoiceState _state;

  @override
  VoiceState build() => _state;
}

