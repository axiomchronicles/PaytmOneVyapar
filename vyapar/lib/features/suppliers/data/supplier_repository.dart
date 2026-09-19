import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';
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

  Future<List<NearbySupplier>> discoverNearbySuppliers({
    String? search,
    String? city,
    String? category,
    double? radiusKm,
  }) async {
    try {
      final response = await _dio.get<Object?>(
        '/suppliers/discovery/nearby',
        queryParameters: {
          if (search != null && search.isNotEmpty) 'search': search,
          if (city != null && city.isNotEmpty) 'city': city,
          if (category != null && category.isNotEmpty) 'category': category,
          if (radiusKm != null) 'radius_km': radiusKm,
          'limit': 50,
        },
      );
      final body = jsonMap(response.data);
      return jsonList(body['items'])
          .map((item) => NearbySupplier.fromJson(jsonMap(item)))
          .toList(growable: false);
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<List<NearbyMerchant>> discoverNearbyMerchants({
    String? search,
    String? city,
    String? pincode,
  }) async {
    try {
      final response = await _dio.get<Object?>(
        '/suppliers/discovery/merchants',
        queryParameters: {
          if (search != null && search.isNotEmpty) 'search': search,
          if (city != null && city.isNotEmpty) 'city': city,
          if (pincode != null && pincode.isNotEmpty) 'pincode': pincode,
          'limit': 50,
        },
      );
      final body = jsonMap(response.data);
      return jsonList(body['items'])
          .map((item) => NearbyMerchant.fromJson(jsonMap(item)))
          .toList(growable: false);
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<SupplierDetail> getMySupplierProfile() async {
    try {
      final response = await _dio.get<Object?>('/suppliers/me');
      return SupplierDetail.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<List<OrderDetail>> getMySupplierOrders({String? status}) async {
    try {
      final response = await _dio.get<Object?>(
        '/suppliers/me/orders',
        queryParameters: {
          if (status != null && status.isNotEmpty) 'status': status,
          'limit': 50,
        },
      );
      final body = jsonMap(response.data);
      return jsonList(body['items'])
          .map((item) => OrderDetail.fromJson(jsonMap(item)))
          .toList(growable: false);
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<SupplierProduct> upsertMyProduct({
    required String sku,
    required String name,
    required String unit,
    required double availableQuantity,
    required double unitPrice,
    required int leadTimeDays,
    String? category,
    String? supplierSku,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/suppliers/me/products',
        data: {
          'sku': sku,
          'name': name,
          'unit': unit,
          'available_quantity': availableQuantity,
          'unit_price': unitPrice,
          'lead_time_days': leadTimeDays,
          if (category != null && category.isNotEmpty) 'category': category,
          if (supplierSku != null && supplierSku.isNotEmpty)
            'supplier_sku': supplierSku,
        },
      );
      return SupplierProduct.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<OrderDetail> decideMyOrder({
    required String orderId,
    required bool approved,
    required String idempotencyKey,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/suppliers/me/orders/$orderId/decision',
        data: {'approved': approved, 'idempotency_key': idempotencyKey},
      );
      return OrderDetail.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
