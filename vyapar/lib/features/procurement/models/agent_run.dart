import 'package:vyapar/core/networking/json.dart';

class AgentRunRequest {
  const AgentRunRequest({
    required this.requestId,
    required this.storeId,
    required this.sku,
    required this.quantityOnHand,
    required this.reorderPoint,
    required this.requiredQuantity,
    required this.unit,
    required this.targetPrice,
    required this.maxPrice,
    required this.spendingLimit,
    required this.deliveryDeadline,
    required this.salesHistory,
    this.safetyStock = 2,
  });

  final String requestId;
  final String storeId;
  final String sku;
  final double quantityOnHand;
  final double reorderPoint;
  final double safetyStock;
  final double requiredQuantity;
  final String unit;
  final double targetPrice;
  final double maxPrice;
  final double spendingLimit;
  final DateTime deliveryDeadline;
  final List<JsonMap> salesHistory;

  JsonMap toJson() => {
    'request_id': requestId,
    'store_id': storeId,
    'sku': sku,
    'quantity_on_hand': quantityOnHand,
    'reorder_point': reorderPoint,
    'safety_stock': safetyStock,
    'required_quantity': requiredQuantity,
    'unit': unit,
    'target_price': targetPrice,
    'max_price': maxPrice,
    'spending_limit': spendingLimit,
    'delivery_deadline': deliveryDeadline.toIso8601String(),
    'sales_history': salesHistory,
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
