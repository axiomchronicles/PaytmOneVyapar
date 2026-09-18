import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/analytics/models/analytics_overview.dart';

class AnalyticsRepository {
  AnalyticsRepository(this._dio);

  final Dio _dio;

  Future<AnalyticsOverview> getOverview() async {
    try {
      final response = await _dio.get<Object?>('/analytics/overview');
      return AnalyticsOverview.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
