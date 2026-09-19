import 'package:vyapar/core/networking/json.dart';

class NegotiationDetail {
  const NegotiationDetail({
    required this.id,
    required this.supplierId,
    required this.supplierName,
    required this.correlationId,
    required this.sku,
    required this.status,
    required this.roundCount,
    required this.history,
    required this.createdAt,
    this.storeId,
    this.workflowRequestId,
    this.proposalId,
    this.approvalId,
    this.constraints = const {},
    this.currentQuote,
    this.updatedAt,
  });

  factory NegotiationDetail.fromJson(JsonMap json) => NegotiationDetail(
    id: jsonString(json['id'], 'id'),
    supplierId: jsonString(json['supplier_id'], 'supplier_id'),
    supplierName: jsonString(json['supplier_name'], 'supplier_name'),
    correlationId: jsonString(json['correlation_id'], 'correlation_id'),
    storeId: jsonOptionalString(json['store_id']),
    workflowRequestId: jsonOptionalString(json['workflow_request_id']),
    proposalId: jsonOptionalString(json['proposal_id']),
    approvalId: jsonOptionalString(json['approval_id']),
    sku: jsonString(json['sku'], 'sku'),
    status: jsonString(json['status'], 'status'),
    roundCount: jsonNumber(json['round_count'], 'round_count').toInt(),
    constraints: json['constraints'] is Map
        ? jsonMap(json['constraints'])
        : const {},
    history: json['history'] is List
        ? jsonList(json['history']).map(jsonMap).toList(growable: false)
        : const [],
    currentQuote: json['current_quote'] is Map
        ? jsonMap(json['current_quote'])
        : null,
    createdAt: DateTime.parse(jsonString(json['created_at'], 'created_at')),
    updatedAt: json['updated_at'] != null
        ? DateTime.tryParse(json['updated_at'].toString())
        : null,
  );

  final String id;
  final String supplierId;
  final String supplierName;
  final String correlationId;
  final String? storeId;
  final String? workflowRequestId;
  final String? proposalId;
  final String? approvalId;
  final String sku;
  final String status;
  final int roundCount;
  final JsonMap constraints;
  final List<JsonMap> history;
  final JsonMap? currentQuote;
  final DateTime createdAt;
  final DateTime? updatedAt;

  num? get targetPrice {
    final v = constraints['target_price'];
    return v != null ? num.tryParse(v.toString()) : null;
  }

  num? get maxPrice {
    final v = constraints['max_price'];
    return v != null ? num.tryParse(v.toString()) : null;
  }

  num? get quantity {
    final v = constraints['quantity'] ?? currentQuote?['quantity'];
    return v != null ? num.tryParse(v.toString()) : null;
  }

  num? get initialQuotePrice {
    for (final event in history) {
      final eventType = event['event']?.toString().toUpperCase();
      if (eventType == 'BUYER_RFQ') continue;
      final price = event['unit_price'];
      if (price != null) {
        final parsed = num.tryParse(price.toString());
        if (parsed != null && parsed > 0) return parsed;
      }
    }
    return null;
  }

  num? get finalPrice {
    final quotePrice = currentQuote?['unit_price'];
    if (quotePrice != null) {
      final parsed = num.tryParse(quotePrice.toString());
      if (parsed != null) return parsed;
    }
    for (final event in history.reversed) {
      final price = event['unit_price'];
      if (price != null) {
        final parsed = num.tryParse(price.toString());
        if (parsed != null) return parsed;
      }
    }
    return null;
  }

  num? get savingsPerUnit {
    final initial = initialQuotePrice;
    final fin = finalPrice;
    if (initial != null && fin != null && initial > fin) {
      return initial - fin;
    }
    return null;
  }

  double? get savingsPercent {
    final initial = initialQuotePrice;
    final savings = savingsPerUnit;
    if (initial != null && savings != null && initial > 0) {
      return (savings / initial) * 100;
    }
    return null;
  }
}
