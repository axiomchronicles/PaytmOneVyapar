import 'package:vyapar/core/networking/json.dart';

class AgentRunRequest {
  const AgentRunRequest({
    required this.requestId,
    required this.storeId,
    required this.sku,
    required this.requiredQuantity,
    required this.targetPrice,
    required this.maxPrice,
    required this.deliveryDeadline,
    this.safetyStock = 2,
  });

  final String requestId;
  final String storeId;
  final String sku;
  final double safetyStock;
  final double requiredQuantity;
  final double targetPrice;
  final double maxPrice;
  final DateTime deliveryDeadline;

  JsonMap toJson() => {
    'request_id': requestId,
    'store_id': storeId,
    'sku': sku,
    'safety_stock': safetyStock,
    'required_quantity': requiredQuantity,
    'target_price': targetPrice,
    'max_price': maxPrice,
    'delivery_deadline': deliveryDeadline.toIso8601String(),
  };
}

class AgentRunResult {
  const AgentRunResult({
    required this.requestId,
    required this.state,
    this.approvalId,
    this.approvalToken,
  });

  factory AgentRunResult.fromJson(JsonMap json) {
    final state = jsonMap(json['state']);
    return AgentRunResult(
      requestId: jsonString(json['request_id'], 'request_id'),
      state: state,
      approvalId: jsonOptionalString(state['approval_id']),
      approvalToken: jsonOptionalString(state['approval_token']),
    );
  }

  final String requestId;
  final JsonMap state;
  final String? approvalId;
  final String? approvalToken;
}
