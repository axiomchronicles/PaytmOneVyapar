import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/notifications/models/notification_item.dart';

class NotificationRepository {
  NotificationRepository(this._dio);

  final Dio _dio;

  Future<CursorPage<NotificationItem>> list({String? cursor}) async {
    try {
      final response = await _dio.get<Object?>(
        '/notifications',
        queryParameters: {'limit': 30, if (cursor != null) 'cursor': cursor},
      );
      return CursorPage.fromJson(
        jsonMap(response.data),
        NotificationItem.fromJson,
      );
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<NotificationItem> markRead(String id) async {
    try {
      final response = await _dio.patch<Object?>('/notifications/$id/read');
      return NotificationItem.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<void> markAllRead() async {
    try {
      await _dio.post<void>('/notifications/read-all');
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
