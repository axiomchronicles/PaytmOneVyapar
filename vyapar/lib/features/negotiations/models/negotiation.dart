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
    this.currentQuote,
  });

  factory NegotiationDetail.fromJson(JsonMap json) => NegotiationDetail(
    id: jsonString(json['id'], 'id'),
    supplierId: jsonString(json['supplier_id'], 'supplier_id'),
    supplierName: jsonString(json['supplier_name'], 'supplier_name'),
    correlationId: jsonString(json['correlation_id'], 'correlation_id'),
    sku: jsonString(json['sku'], 'sku'),
    status: jsonString(json['status'], 'status'),
    roundCount: jsonNumber(json['round_count'], 'round_count').toInt(),
    history: json['history'] is List
        ? jsonList(json['history']).map(jsonMap).toList(growable: false)
        : const [],
    currentQuote: json['current_quote'] is Map
        ? jsonMap(json['current_quote'])
        : null,
    createdAt: DateTime.parse(jsonString(json['created_at'], 'created_at')),
  );

  final String id;
  final String supplierId;
  final String supplierName;
  final String correlationId;
  final String sku;
  final String status;
  final int roundCount;
  final List<JsonMap> history;
  final JsonMap? currentQuote;
  final DateTime createdAt;
}
