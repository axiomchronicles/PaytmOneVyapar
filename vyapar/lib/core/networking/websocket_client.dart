import 'dart:async';
import 'dart:convert';

import 'package:vyapar/core/config/app_config.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/core/networking/realtime_event.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class RealtimeClient {
  RealtimeClient({required AppConfig config, required this.token})
    : _uri = config.websocketUri('/ws');

  final Uri _uri;
  final String token;
  bool _closed = false;
  WebSocketChannel? _channel;

  Stream<RealtimeEvent> events() async* {
    var retry = 0;
    while (!_closed) {
      try {
        final channel = IOWebSocketChannel.connect(
          _uri,
          headers: {'Authorization': 'Bearer $token'},
          pingInterval: const Duration(seconds: 25),
          connectTimeout: const Duration(seconds: 10),
        );
        _channel = channel;
        await channel.ready;
        retry = 0;
        await for (final message in channel.stream) {
          if (_closed) return;
          if (message is! String) continue;
          final decoded = jsonDecode(message);
          if (decoded is! Map) continue;
          try {
            yield RealtimeEvent.fromJson(jsonMap(decoded));
          } on FormatException {
            continue;
          }
        }
      } catch (_) {
        if (_closed) return;
      } finally {
        await _channel?.sink.close();
        _channel = null;
      }
      if (_closed) return;
      retry = (retry + 1).clamp(1, 5);
      await Future<void>.delayed(Duration(seconds: 1 << (retry - 1)));
    }
  }

  Future<void> close() async {
    _closed = true;
    await _channel?.sink.close();
    _channel = null;
  }
}
