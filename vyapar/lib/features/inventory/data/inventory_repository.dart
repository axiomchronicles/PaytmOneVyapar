import 'package:dio/dio.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/inventory/data/receipt_image_picker.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/models/receipt_scan.dart';

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

  Future<ReceiptScanReview> scanReceipt(ReceiptImageInput image) async {
    if (image.bytes.length > 10 * 1024 * 1024) {
      throw const AppFailure(
        kind: FailureKind.validation,
        message: 'Choose an image smaller than 10 MB.',
        code: 'IMAGE_TOO_LARGE',
      );
    }
    try {
      final response = await _dio.post<Object?>(
        '/inventory/scan-receipt',
        data: FormData.fromMap({
          'image': MultipartFile.fromBytes(
            image.bytes,
            filename: image.filename,
            contentType: DioMediaType.parse(image.contentType),
          ),
        }),
        options: Options(
          sendTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 60),
        ),
      );
      return ReceiptScanReview.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<ReceiptConfirmation> confirmReceipt({
    required ReceiptScanReview review,
    required String storeId,
    required String idempotencyKey,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/inventory/scan-receipt/confirm',
        data: {
          'scan_id': review.scanId,
          'store_id': storeId,
          'idempotency_key': idempotencyKey,
          'receipt': review.receipt.toJson(),
          'items': review.items
              .map((item) => item.toConfirmJson())
              .toList(growable: false),
        },
        options: Options(receiveTimeout: const Duration(seconds: 40)),
      );
      return ReceiptConfirmation.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<ReceiptConfirmation> confirmManualInventory({
    required ReceiptScanReview review,
    required String storeId,
    required String idempotencyKey,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/inventory/manual',
        data: {
          'batch_id': review.scanId,
          'store_id': storeId,
          'idempotency_key': idempotencyKey,
          'items': review.items
              .map((item) => item.toConfirmJson())
              .toList(growable: false),
        },
      );
      return ReceiptConfirmation.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
