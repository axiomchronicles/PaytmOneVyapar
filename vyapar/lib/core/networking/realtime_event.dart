import 'package:vyapar/core/networking/json.dart';

enum RealtimeConnectionState { connecting, connected, disconnected }

class RealtimeEvent {
  const RealtimeEvent({required this.type, required this.data});

  final String type;
  final JsonMap data;

  factory RealtimeEvent.fromJson(JsonMap json) => RealtimeEvent(
    type: jsonString(json['type'], 'type'),
    data: json['data'] is Map ? jsonMap(json['data']) : const {},
  );
}
