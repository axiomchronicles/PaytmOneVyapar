import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/negotiations/models/negotiation.dart';

class NegotiationRepository {
  NegotiationRepository(this._dio);

  final Dio _dio;

  Future<CursorPage<NegotiationDetail>> list({String? cursor}) async {
    try {
      final response = await _dio.get<Object?>(
        '/negotiations',
        queryParameters: {'limit': 30, if (cursor != null) 'cursor': cursor},
      );
      return CursorPage.fromJson(
        jsonMap(response.data),
        NegotiationDetail.fromJson,
      );
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<NegotiationDetail> get(String id) async {
    try {
      final response = await _dio.get<Object?>('/negotiations/$id');
      return NegotiationDetail.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
