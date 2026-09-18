import 'package:decimal/decimal.dart';
import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';

enum ApprovalAction { approve, modify, reject }

class ApprovalRepository {
  ApprovalRepository(this._dio, [Uuid? uuid]) : _uuid = uuid ?? const Uuid();

  final Dio _dio;
  final Uuid _uuid;

  Future<ApprovalDetail> get(String approvalId) async {
    try {
      final response = await _dio.get<Object?>('/approvals/$approvalId');
      return ApprovalDetail.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<CursorPage<ApprovalDetail>> list({
    String? cursor,
    String? status,
  }) async {
    try {
      final response = await _dio.get<Object?>(
        '/approvals',
        queryParameters: {
          'limit': 30,
          if (cursor != null) 'cursor': cursor,
          if (status != null) 'status': status,
        },
      );
      return CursorPage.fromJson(
        jsonMap(response.data),
        ApprovalDetail.fromJson,
      );
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<ApprovalActionResult> decide({
    required String approvalId,
    required ApprovalAction action,
    ApprovalActionContext? context,
    Decimal? quantity,
    Decimal? maxUnitPrice,
  }) async {
    if (action != ApprovalAction.reject && context == null) {
      throw StateError('The exact approval token is unavailable.');
    }
    if (action == ApprovalAction.modify && context?.requestId == null) {
      throw StateError(
        'The workflow request ID is required to modify this proposal.',
      );
    }
    final data = <String, Object?>{
      'idempotency_key': _uuid.v4(),
      if (action != ApprovalAction.reject)
        'approval_token': context?.approvalToken,
      if (context?.requestId case final requestId?) 'request_id': requestId,
      if (quantity != null) 'quantity': quantity.toString(),
      if (maxUnitPrice != null) 'max_unit_price': maxUnitPrice.toString(),
    };
    try {
      final response = await _dio.post<Object?>(
        '/approvals/$approvalId/${action.name}',
        data: data,
      );
      return _parseAction(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  ApprovalActionResult _parseAction(JsonMap body) {
    final workflow = body['workflow'] is Map
        ? jsonMap(body['workflow'])
        : const <String, Object?>{};
    final execution = workflow['execution_result'] is Map
        ? jsonMap(workflow['execution_result'])
        : const <String, Object?>{};
    return ApprovalActionResult(
      approvalId:
          jsonOptionalString(workflow['approval_id']) ??
          jsonOptionalString(body['approval_id']),
      orderId: jsonOptionalString(execution['order_id']),
      status:
          jsonOptionalString(workflow['approval_status']) ??
          jsonOptionalString(body['status']),
    );
  }
}
