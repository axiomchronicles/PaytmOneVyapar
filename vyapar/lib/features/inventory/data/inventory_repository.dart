import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';

class InventoryRepository {
  InventoryRepository(this._dio);

  final Dio _dio;

  Future<List<InventoryItem>> list({
    String? storeId,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await _dio.get<Object?>(
        '/inventory',
        queryParameters: storeId == null ? null : {'store_id': storeId},
        cancelToken: cancelToken,
      );
      return jsonList(response.data)
          .map((item) => InventoryItem.fromJson(jsonMap(item)))
          .toList(growable: false);
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<double> recordEvent({
    required InventoryItem item,
    required double quantityDelta,
    required String eventType,
    required String idempotencyKey,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/inventory/events',
        data: {
          'store_id': item.storeId,
          'product_id': item.productId,
          'quantity_delta': quantityDelta,
          'event_type': eventType,
          'source': 'FLUTTER',
          'idempotency_key': idempotencyKey,
        },
      );
      return jsonNumber(
        jsonMap(response.data)['quantity_on_hand'],
        'quantity_on_hand',
      ).toDouble();
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
