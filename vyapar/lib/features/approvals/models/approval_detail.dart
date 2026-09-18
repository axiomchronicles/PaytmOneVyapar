import 'package:decimal/decimal.dart';
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
    quantity: Decimal.parse(json['quantity'].toString()),
    unit: jsonString(json['unit'], 'unit'),
    unitPrice: Decimal.parse(json['unit_price'].toString()),
    currency: jsonString(json['currency'], 'currency'),
    deliveryAt: DateTime.parse(jsonString(json['delivery_at'], 'delivery_at')),
    quoteId: jsonString(json['quote_id'], 'quote_id'),
  );

  final String proposalId;
  final String storeId;
  final String supplierId;
  final String sku;
  final Decimal quantity;
  final String unit;
  final Decimal unitPrice;
  final String currency;
  final DateTime deliveryAt;
  final String quoteId;

  Decimal get totalAmount => quantity * unitPrice;
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
    this.revision = 1,
    this.workflowRequestId,
    this.actionToken,
    this.decidedAt,
  });

  factory ApprovalDetail.fromJson(JsonMap json) => ApprovalDetail(
    id: jsonString(json['id'], 'id'),
    proposalId: jsonString(json['proposal_id'], 'proposal_id'),
    orderHash: jsonString(json['order_hash'], 'order_hash'),
    proposal: ProposalDetail.fromJson(jsonMap(json['proposal'])),
    status: jsonString(json['status'], 'status'),
    expiresAt: DateTime.parse(jsonString(json['expires_at'], 'expires_at')),
    createdAt: DateTime.parse(jsonString(json['created_at'], 'created_at')),
    revision: json['revision'] == null
        ? 1
        : jsonNumber(json['revision'], 'revision').toInt(),
    workflowRequestId: jsonOptionalString(json['workflow_request_id']),
    actionToken: jsonOptionalString(json['action_token']),
    decidedAt: jsonOptionalString(json['decided_at']) == null
        ? null
        : DateTime.parse(jsonString(json['decided_at'], 'decided_at')),
  );

  final String id;
  final String proposalId;
  final String orderHash;
  final ProposalDetail proposal;
  final String status;
  final DateTime expiresAt;
  final DateTime createdAt;
  final int revision;
  final String? workflowRequestId;
  final String? actionToken;
  final DateTime? decidedAt;

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
