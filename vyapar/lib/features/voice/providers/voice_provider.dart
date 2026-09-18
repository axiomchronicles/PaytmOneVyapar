import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:record/record.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/features/voice/data/pcm_stream_player.dart';
import 'package:vyapar/features/voice/data/voice_repository.dart';
import 'package:vyapar/features/voice/models/voice_models.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

final voiceRepositoryProvider = Provider<VoiceRepository>(
  (ref) => VoiceRepository(ref.watch(dioProvider)),
);

final microphoneProvider = Provider<AudioRecorder>((ref) {
  final recorder = AudioRecorder();
  ref.onDispose(() => unawaited(recorder.dispose()));
  return recorder;
});

final pcmStreamPlayerProvider = Provider<PcmStreamPlayer>((ref) {
  final player = NativePcmStreamPlayer(
    sampleRate: ref.watch(appConfigProvider).voiceOutputSampleRate,
  );
  ref.onDispose(() => unawaited(player.dispose()));
  return player;
});

class VoiceController extends Notifier<VoiceState> {
  late final AudioRecorder _recorder;
  late final PcmStreamPlayer _player;
  WebSocketChannel? _channel;
  StreamSubscription<Object?>? _socketSubscription;
  StreamSubscription<Uint8List>? _microphoneSubscription;

  @override
  VoiceState build() {
    _recorder = ref.watch(microphoneProvider);
    _player = ref.watch(pcmStreamPlayerProvider);
    ref.onDispose(() => unawaited(_disposeSession()));
    return const VoiceState();
  }

  Future<void> start({
    String languageCode = 'auto',
    String? approvalId,
    String? proposalId,
  }) async {
    await _disposeSession();
    state = const VoiceState(phase: VoicePhase.requestingPermission);
    if (!await _recorder.hasPermission()) {
      state = const VoiceState(phase: VoicePhase.permissionDenied);
      return;
    }
    state = state.copyWith(phase: VoicePhase.connecting, clearError: true);
    try {
      final approvalContext = approvalId == null
          ? null
          : ref.read(approvalContextsProvider)[approvalId];
      final session = await ref
          .read(voiceRepositoryProvider)
          .createSession(
            languageCode: languageCode,
            proposalId: proposalId,
            requestId: approvalContext?.requestId,
            approvalToken: approvalContext?.approvalToken,
          );
      if (!session.providerAvailable) {
        state = VoiceState(
          phase: VoicePhase.error,
          sessionId: session.sessionId,
          errorMessage: 'Voice is not configured on this backend.',
        );
        return;
      }
      final config = ref.read(appConfigProvider);
      final token = ref.read(tokenStoreProvider).accessToken;
      if (token == null) {
        throw StateError('Authenticated session is unavailable.');
      }
      final uri = config.websocketUriFromApiPath(session.streamPath);
      final channel = IOWebSocketChannel.connect(
        uri,
        headers: {'Authorization': 'Bearer $token'},
        pingInterval: const Duration(seconds: 20),
        connectTimeout: const Duration(seconds: 10),
      );
      _channel = channel;
      await channel.ready;
      _socketSubscription = channel.stream.listen(
        _handleSocketMessage,
        onError: _handleSocketError,
        onDone: _handleSocketDone,
      );
      final microphone = await _recorder.startStream(
        const RecordConfig(
          encoder: AudioEncoder.pcm16bits,
          sampleRate: 16000,
          numChannels: 1,
          echoCancel: true,
          noiseSuppress: true,
          streamBufferSize: 3200,
        ),
      );
      _microphoneSubscription = microphone.listen(channel.sink.add);
      state = VoiceState(
        phase: VoicePhase.listening,
        sessionId: session.sessionId,
        playbackSupported: session.outputCodec?.toLowerCase() == 'linear16',
      );
    } catch (error) {
      await _disposeSession();
      state = VoiceState(
        phase: VoicePhase.error,
        errorMessage: mapApiError(error).message,
      );
    }
  }

  Future<void> interrupt() async {
    _channel?.sink.add(jsonEncode({'type': 'interrupt'}));
    await _player.flush();
    state = state.copyWith(phase: VoicePhase.interrupted);
  }

  Future<void> stop() async {
    _channel?.sink.add(jsonEncode({'type': 'end'}));
    await _disposeSession();
    state = state.copyWith(phase: VoicePhase.disconnected);
  }

  Future<void> _handleSocketMessage(Object? message) async {
    if (message is List<int>) {
      if (state.playbackSupported) {
        await ref
            .read(pcmStreamPlayerProvider)
            .append(Uint8List.fromList(message));
      }
      return;
    }
    if (message is! String) return;
    try {
      final decoded = jsonDecode(message);
      if (decoded is! Map) return;
      final event = jsonMap(decoded);
      final type = jsonOptionalString(event['type']);
      switch (type) {
        case 'SESSION_STARTED':
          state = state.copyWith(phase: VoicePhase.listening);
        case 'TRANSCRIPT_PARTIAL':
          state = state.copyWith(
            phase: VoicePhase.listening,
            transcript: jsonOptionalString(event['text']) ?? state.transcript,
          );
        case 'TRANSCRIPT_FINAL':
          state = state.copyWith(
            phase: VoicePhase.thinking,
            transcript: jsonOptionalString(event['text']) ?? state.transcript,
          );
        case 'RESPONSE_TEXT':
          state = state.copyWith(
            phase: VoicePhase.thinking,
            response: jsonOptionalString(event['text']) ?? '',
          );
        case 'AUDIO_START':
          final metadata = event['metadata'] is Map
              ? jsonMap(event['metadata'])
              : const <String, Object?>{};
          final codec = jsonOptionalString(metadata['codec']);
          state = state.copyWith(playbackSupported: codec == 'linear16');
          if (state.playbackSupported) {
            await _player.begin();
          }
          state = state.copyWith(phase: VoicePhase.speaking);
        case 'AUDIO_END':
          if (state.playbackSupported) {
            await _player.finish();
          }
          state = state.copyWith(phase: VoicePhase.listening);
        case 'ERROR':
          state = state.copyWith(
            phase: VoicePhase.error,
            errorMessage:
                jsonOptionalString(event['text']) ?? 'Voice session failed.',
          );
        case 'SESSION_ENDED':
          state = state.copyWith(phase: VoicePhase.disconnected);
      }
    } on FormatException {
      return;
    }
  }

  void _handleSocketError(Object error, StackTrace stackTrace) {
    state = state.copyWith(
      phase: VoicePhase.error,
      errorMessage: 'Voice connection interrupted.',
    );
  }

  void _handleSocketDone() {
    if (state.phase != VoicePhase.error) {
      state = state.copyWith(phase: VoicePhase.disconnected);
    }
  }

  Future<void> _disposeSession() async {
    await _microphoneSubscription?.cancel();
    _microphoneSubscription = null;
    if (await _recorder.isRecording()) await _recorder.stop();
    await _socketSubscription?.cancel();
    _socketSubscription = null;
    await _channel?.sink.close();
    _channel = null;
    await _player.flush();
  }
}

final voiceControllerProvider =
    NotifierProvider.autoDispose<VoiceController, VoiceState>(
      VoiceController.new,
    );
