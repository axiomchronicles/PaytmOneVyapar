import 'package:vyapar/core/networking/json.dart';

class NotificationItem {
  const NotificationItem({
    required this.id,
    required this.type,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
    this.entityType,
    this.entityId,
  });

  factory NotificationItem.fromJson(JsonMap json) => NotificationItem(
    id: jsonString(json['id'], 'id'),
    type: jsonString(json['notification_type'], 'notification_type'),
    title: jsonString(json['title'], 'title'),
    body: jsonString(json['body'], 'body'),
    isRead: jsonBool(json['is_read'], 'is_read'),
    createdAt: DateTime.parse(jsonString(json['created_at'], 'created_at')),
    entityType: jsonOptionalString(json['entity_type']),
    entityId: jsonOptionalString(json['entity_id']),
  );

  final String id;
  final String type;
  final String title;
  final String body;
  final bool isRead;
  final DateTime createdAt;
  final String? entityType;
  final String? entityId;
}
