import 'package:vyapar/core/networking/json.dart';

class OrderDetail {
  const OrderDetail({
    required this.id,
    required this.proposalId,
    required this.supplierId,
    required this.status,
    required this.totalAmount,
    required this.currency,
    required this.createdAt,
    this.supplierReference,
    this.failureReason,
  });

  factory OrderDetail.fromJson(JsonMap json) => OrderDetail(
    id: jsonString(json['id'], 'id'),
    proposalId: jsonString(json['proposal_id'], 'proposal_id'),
    supplierId: jsonString(json['supplier_id'], 'supplier_id'),
    status: jsonString(json['status'], 'status'),
    totalAmount: jsonNumber(json['total_amount'], 'total_amount').toDouble(),
    currency: jsonString(json['currency'], 'currency'),
    supplierReference: jsonOptionalString(json['supplier_reference']),
    failureReason: jsonOptionalString(json['failure_reason']),
    createdAt: DateTime.parse(jsonString(json['created_at'], 'created_at')),
  );

  final String id;
  final String proposalId;
  final String supplierId;
  final String status;
  final double totalAmount;
  final String currency;
  final String? supplierReference;
  final String? failureReason;
  final DateTime createdAt;
}
