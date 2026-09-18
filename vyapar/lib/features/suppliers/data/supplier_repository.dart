import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/suppliers/models/supplier.dart';

class SupplierRepository {
  SupplierRepository(this._dio);

  final Dio _dio;

  Future<CursorPage<SupplierDetail>> list({
    String? cursor,
    String? search,
  }) async {
    try {
      final response = await _dio.get<Object?>(
        '/suppliers',
        queryParameters: {
          'limit': 30,
          if (cursor != null) 'cursor': cursor,
          if (search != null && search.isNotEmpty) 'search': search,
        },
      );
      return CursorPage.fromJson(
        jsonMap(response.data),
        SupplierDetail.fromJson,
      );
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<SupplierDetail> get(String id) async {
    try {
      final response = await _dio.get<Object?>('/suppliers/$id');
      return SupplierDetail.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
