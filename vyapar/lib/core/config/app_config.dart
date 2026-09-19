import 'package:flutter/foundation.dart';

class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.voiceOutputCodec,
    required this.voiceOutputSampleRate,
  });

  factory AppConfig.current() {
    const configuredBase = String.fromEnvironment('API_BASE_URL');
    final host = defaultTargetPlatform == TargetPlatform.android
        ? '10.0.2.2'
        : '127.0.0.1';
    final base = configuredBase.isEmpty
        ? 'http://$host:8000/api/v1'
        : configuredBase;
    return AppConfig(
      apiBaseUrl: base.replaceFirst(RegExp(r'/+$'), ''),
      voiceOutputCodec: const String.fromEnvironment(
        'VOICE_OUTPUT_CODEC',
        defaultValue: 'linear16',
      ),
      voiceOutputSampleRate: const int.fromEnvironment(
        'VOICE_OUTPUT_SAMPLE_RATE',
        defaultValue: 24000,
      ),
    );
  }

  final String apiBaseUrl;
  final String voiceOutputCodec;
  final int voiceOutputSampleRate;

  Uri websocketUri(String path) {
    final base = Uri.parse(apiBaseUrl);
    return base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: '${base.path}${path.startsWith('/') ? path : '/$path'}',
      query: null,
    );
  }

  Uri websocketUriFromApiPath(String path) {
    final base = Uri.parse(apiBaseUrl);
    final apiPrefix = base.path.endsWith('/api/v1') ? base.path : '/api/v1';
    return base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: path.startsWith('/') ? path : '$apiPrefix/$path',
      query: null,
    );
  }
}
