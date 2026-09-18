import 'package:vyapar/core/networking/json.dart';

enum RealtimeConnectionState { connecting, connected, disconnected }

class RealtimeEvent {
  const RealtimeEvent({
    required this.type,
    required this.data,
    this.eventId,
    this.occurredAt,
    this.version = 1,
  });

  final String type;
  final JsonMap data;
  final String? eventId;
  final DateTime? occurredAt;
  final int version;

  factory RealtimeEvent.fromJson(JsonMap json) => RealtimeEvent(
    type: jsonString(json['event_type'] ?? json['type'], 'event_type'),
    data: json['payload'] is Map
        ? jsonMap(json['payload'])
        : json['data'] is Map
        ? jsonMap(json['data'])
        : const {},
    eventId: jsonOptionalString(json['event_id']),
    occurredAt: jsonOptionalString(json['occurred_at']) == null
        ? null
        : DateTime.parse(jsonString(json['occurred_at'], 'occurred_at')),
    version: json['version'] == null
        ? 1
        : jsonNumber(json['version'], 'version').toInt(),
  );
}
