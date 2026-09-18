import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';

class OrderRepository {
  OrderRepository(this._dio);

  final Dio _dio;

  Future<OrderDetail> get(String orderId) async {
    try {
      final response = await _dio.get<Object?>('/orders/$orderId');
      return OrderDetail.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<CursorPage<OrderDetail>> list({String? cursor}) async {
    try {
      final response = await _dio.get<Object?>(
        '/orders',
        queryParameters: {'limit': 30, if (cursor != null) 'cursor': cursor},
      );
      return CursorPage.fromJson(jsonMap(response.data), OrderDetail.fromJson);
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
