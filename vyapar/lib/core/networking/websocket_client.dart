import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'dart:math';

import 'package:vyapar/core/config/app_config.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/core/networking/realtime_event.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class RealtimeEventDeduplicator {
  RealtimeEventDeduplicator({this.capacity = 512});

  final int capacity;
  final Queue<String> _recentIds = Queue<String>();
  final Set<String> _seenIds = <String>{};

  bool accept(String? eventId) {
    if (eventId == null) return true;
    if (!_seenIds.add(eventId)) return false;
    _recentIds.addLast(eventId);
    if (_recentIds.length > capacity) _seenIds.remove(_recentIds.removeFirst());
    return true;
  }
}

class RealtimeCoordinator {
  RealtimeCoordinator({required AppConfig config, required this.token})
    : _uri = config.websocketUri('/ws');

  final Uri _uri;
  final String token;
  bool _closed = false;
  WebSocketChannel? _channel;
  final RealtimeEventDeduplicator _deduplicator = RealtimeEventDeduplicator();

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
        yield const RealtimeEvent(
          type: 'REALTIME_RESYNC_REQUIRED',
          data: <String, Object?>{},
        );
        await for (final message in channel.stream) {
          if (_closed) return;
          if (message is! String) continue;
          final decoded = jsonDecode(message);
          if (decoded is! Map) continue;
          try {
            final event = RealtimeEvent.fromJson(jsonMap(decoded));
            final eventId = event.eventId;
            if (!_deduplicator.accept(eventId)) continue;
            if (event.type != 'HEARTBEAT') yield event;
          } on FormatException {
            continue;
          }
        }
      } catch (_) {
        if (_closed) return;
      } finally {
        final unauthorized = _channel?.closeCode == 4401;
        await _channel?.sink.close();
        _channel = null;
        if (unauthorized && !_closed) {
          yield const RealtimeEvent(
            type: 'REALTIME_AUTH_FAILED',
            data: <String, Object?>{},
          );
          _closed = true;
        }
      }
      if (_closed) return;
      retry = (retry + 1).clamp(1, 5);
      final base = 1 << (retry - 1);
      final jitterMs = Random.secure().nextInt(500);
      await Future<void>.delayed(
        Duration(seconds: base, milliseconds: jitterMs),
      );
    }
  }

  Future<void> close() async {
    _closed = true;
    await _channel?.sink.close();
    _channel = null;
  }
}
