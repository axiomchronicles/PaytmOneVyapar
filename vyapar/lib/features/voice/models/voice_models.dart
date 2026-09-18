import 'package:vyapar/core/networking/json.dart';

enum VoicePhase {
  idle,
  requestingPermission,
  permissionDenied,
  connecting,
  listening,
  thinking,
  speaking,
  interrupted,
  disconnected,
  error,
}

class VoiceSessionInfo {
  const VoiceSessionInfo({
    required this.sessionId,
    required this.streamPath,
    required this.providerAvailable,
    required this.inputEncoding,
    required this.inputSampleRate,
  });

  factory VoiceSessionInfo.fromJson(JsonMap json) {
    final audio = jsonMap(json['audio']);
    return VoiceSessionInfo(
      sessionId: jsonString(json['session_id'], 'session_id'),
      streamPath: jsonString(json['stream_url'], 'stream_url'),
      providerAvailable: jsonBool(
        json['provider_available'],
        'provider_available',
      ),
      inputEncoding: jsonString(audio['encoding'], 'encoding'),
      inputSampleRate: jsonNumber(audio['sample_rate'], 'sample_rate').toInt(),
    );
  }

  final String sessionId;
  final String streamPath;
  final bool providerAvailable;
  final String inputEncoding;
  final int inputSampleRate;
}

class VoiceState {
  const VoiceState({
    this.phase = VoicePhase.idle,
    this.transcript = '',
    this.response = '',
    this.errorMessage,
    this.sessionId,
    this.playbackSupported = true,
  });

  final VoicePhase phase;
  final String transcript;
  final String response;
  final String? errorMessage;
  final String? sessionId;
  final bool playbackSupported;

  VoiceState copyWith({
    VoicePhase? phase,
    String? transcript,
    String? response,
    String? errorMessage,
    String? sessionId,
    bool? playbackSupported,
    bool clearError = false,
  }) => VoiceState(
    phase: phase ?? this.phase,
    transcript: transcript ?? this.transcript,
    response: response ?? this.response,
    errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
    sessionId: sessionId ?? this.sessionId,
    playbackSupported: playbackSupported ?? this.playbackSupported,
  );
}
