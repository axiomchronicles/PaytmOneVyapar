import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/recommendations/models/recommendation.dart';

class RecommendationRepository {
  RecommendationRepository(this._dio);

  final Dio _dio;

  Future<List<Recommendation>> list() async {
    try {
      final response = await _dio.get<Object?>('/recommendations');
      return jsonList(response.data)
          .map((item) => Recommendation.fromJson(jsonMap(item)))
          .toList(growable: false);
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
