import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/activity/models/activity.dart';

class ActivityRepository {
  ActivityRepository(this._dio);

  final Dio _dio;

  Future<CursorPage<ActivityItem>> a2a({String? cursor}) =>
      _list('/a2a/activity', cursor, ActivityItem.fromA2A);

  Future<CursorPage<ActivityItem>> business({
    String? cursor,
    DateTime? from,
    DateTime? to,
  }) => _list(
    '/history/activity',
    cursor,
    ActivityItem.fromBusiness,
    from: from,
    to: to,
  );

  Future<List<ActivityItem>> conversation(String correlationId) async {
    try {
      final response = await _dio.get<Object?>(
        '/a2a/conversations/$correlationId',
      );
      return jsonList(response.data)
          .map((item) => ActivityItem.fromA2A(jsonMap(item)))
          .toList(growable: false);
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<CursorPage<ActivityItem>> _list(
    String path,
    String? cursor,
    ActivityItem Function(JsonMap) decode, {
    DateTime? from,
    DateTime? to,
  }) async {
    try {
      final response = await _dio.get<Object?>(
        path,
        queryParameters: {
          'limit': 30,
          if (cursor != null) 'cursor': cursor,
          if (from != null) 'created_from': from.toUtc().toIso8601String(),
          if (to != null) 'created_to': to.toUtc().toIso8601String(),
        },
      );
      return CursorPage.fromJson(jsonMap(response.data), decode);
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
