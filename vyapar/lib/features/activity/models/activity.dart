import 'package:vyapar/core/networking/json.dart';

class ActivityItem {
  const ActivityItem({
    required this.id,
    required this.title,
    required this.kind,
    required this.occurredAt,
    this.subtitle,
    this.entityType,
    this.entityId,
    this.correlationId,
  });

  factory ActivityItem.fromA2A(JsonMap json) => ActivityItem(
    id: jsonString(json['id'], 'id'),
    title: jsonString(json['summary'], 'summary'),
    kind: jsonString(json['intent'], 'intent'),
    subtitle: jsonString(json['direction'], 'direction'),
    occurredAt: DateTime.parse(jsonString(json['occurred_at'], 'occurred_at')),
    entityType: json['order_id'] != null
        ? 'order'
        : json['negotiation_id'] != null
        ? 'negotiation'
        : null,
    entityId:
        jsonOptionalString(json['order_id']) ??
        jsonOptionalString(json['negotiation_id']),
    correlationId: jsonOptionalString(json['correlation_id']),
  );

  factory ActivityItem.fromBusiness(JsonMap json) => ActivityItem(
    id: jsonString(json['id'], 'id'),
    title: jsonString(json['action'], 'action').replaceAll('.', ' '),
    kind: jsonString(json['actor_type'], 'actor_type'),
    subtitle: jsonString(json['resource_type'], 'resource_type'),
    occurredAt: DateTime.parse(jsonString(json['occurred_at'], 'occurred_at')),
    entityType: jsonString(json['resource_type'], 'resource_type'),
    entityId: jsonString(json['resource_id'], 'resource_id'),
  );

  final String id;
  final String title;
  final String kind;
  final String? subtitle;
  final DateTime occurredAt;
  final String? entityType;
  final String? entityId;
  final String? correlationId;
}
