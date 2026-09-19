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

  Future<NegotiationDetail> start({
    required String sku,
    String? storeId,
    num? quantity,
    num? targetPrice,
    num? maxPrice,
    String? supplierId,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/negotiations/start',
        data: {
          'sku': sku,
          if (supplierId != null) 'supplier_id': supplierId,
          if (storeId != null) 'store_id': storeId,
          if (quantity != null) 'quantity': quantity,
          if (targetPrice != null) 'target_price': targetPrice,
          if (maxPrice != null) 'max_price': maxPrice,
        },
      );
      return NegotiationDetail.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
