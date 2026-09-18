import 'package:vyapar/core/networking/json.dart';

class ProposalDetail {
  const ProposalDetail({
    required this.proposalId,
    required this.storeId,
    required this.supplierId,
    required this.sku,
    required this.quantity,
    required this.unit,
    required this.unitPrice,
    required this.currency,
    required this.deliveryAt,
    required this.quoteId,
  });

  factory ProposalDetail.fromJson(JsonMap json) => ProposalDetail(
    proposalId: jsonString(json['proposal_id'], 'proposal_id'),
    storeId: jsonString(json['store_id'], 'store_id'),
    supplierId: jsonString(json['supplier_id'], 'supplier_id'),
    sku: jsonString(json['sku'], 'sku'),
    quantity: jsonNumber(json['quantity'], 'quantity').toDouble(),
    unit: jsonString(json['unit'], 'unit'),
    unitPrice: jsonNumber(json['unit_price'], 'unit_price').toDouble(),
    currency: jsonString(json['currency'], 'currency'),
    deliveryAt: DateTime.parse(jsonString(json['delivery_at'], 'delivery_at')),
    quoteId: jsonString(json['quote_id'], 'quote_id'),
  );

  final String proposalId;
  final String storeId;
  final String supplierId;
  final String sku;
  final double quantity;
  final String unit;
  final double unitPrice;
  final String currency;
  final DateTime deliveryAt;
  final String quoteId;

  double get totalAmount => quantity * unitPrice;
}

class ApprovalDetail {
  const ApprovalDetail({
    required this.id,
    required this.proposalId,
    required this.orderHash,
    required this.proposal,
    required this.status,
    required this.expiresAt,
    required this.createdAt,
  });

  factory ApprovalDetail.fromJson(JsonMap json) => ApprovalDetail(
    id: jsonString(json['id'], 'id'),
    proposalId: jsonString(json['proposal_id'], 'proposal_id'),
    orderHash: jsonString(json['order_hash'], 'order_hash'),
    proposal: ProposalDetail.fromJson(jsonMap(json['proposal'])),
    status: jsonString(json['status'], 'status'),
    expiresAt: DateTime.parse(jsonString(json['expires_at'], 'expires_at')),
    createdAt: DateTime.parse(jsonString(json['created_at'], 'created_at')),
  );

  final String id;
  final String proposalId;
  final String orderHash;
  final ProposalDetail proposal;
  final String status;
  final DateTime expiresAt;
  final DateTime createdAt;

  bool get isPending => status == 'PENDING';
}

class ApprovalActionContext {
  const ApprovalActionContext({required this.approvalToken, this.requestId});

  final String approvalToken;
  final String? requestId;
}

class ApprovalActionResult {
  const ApprovalActionResult({this.approvalId, this.orderId, this.status});

  final String? approvalId;
  final String? orderId;
  final String? status;
}
