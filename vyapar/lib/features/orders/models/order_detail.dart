import 'package:decimal/decimal.dart';
import 'package:vyapar/core/networking/json.dart';

class OrderDetail {
  const OrderDetail({
    required this.id,
    required this.proposalId,
    required this.supplierId,
    required this.supplierName,
    required this.storeId,
    required this.status,
    required this.totalAmount,
    required this.currency,
    required this.createdAt,
    required this.updatedAt,
    this.approvalId,
    this.items = const [],
    this.timeline = const [],
    this.supplierReference,
    this.failureReason,
  });

  factory OrderDetail.fromJson(JsonMap json) => OrderDetail(
    id: jsonString(json['id'], 'id'),
    proposalId: jsonString(json['proposal_id'], 'proposal_id'),
    supplierId: jsonString(json['supplier_id'], 'supplier_id'),
    supplierName:
        jsonOptionalString(json['supplier_name']) ??
        jsonString(json['supplier_id'], 'supplier_id'),
    storeId: jsonOptionalString(json['store_id']) ?? '',
    status: jsonString(json['status'], 'status'),
    totalAmount: Decimal.parse(json['total_amount'].toString()),
    currency: jsonString(json['currency'], 'currency'),
    supplierReference: jsonOptionalString(json['supplier_reference']),
    failureReason: jsonOptionalString(json['failure_reason']),
    createdAt: DateTime.parse(jsonString(json['created_at'], 'created_at')),
    updatedAt: DateTime.parse(
      jsonOptionalString(json['updated_at']) ??
          jsonString(json['created_at'], 'created_at'),
    ),
    approvalId: jsonOptionalString(json['approval_id']),
    items: json['items'] is List
        ? jsonList(json['items'])
              .map((item) => OrderLine.fromJson(jsonMap(item)))
              .toList(growable: false)
        : const [],
    timeline: json['timeline'] is List
        ? jsonList(json['timeline'])
              .map((item) => OrderTimelineEvent.fromJson(jsonMap(item)))
              .toList(growable: false)
        : const [],
  );

  final String id;
  final String proposalId;
  final String supplierId;
  final String supplierName;
  final String storeId;
  final String status;
  final Decimal totalAmount;
  final String currency;
  final String? supplierReference;
  final String? failureReason;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? approvalId;
  final List<OrderLine> items;
  final List<OrderTimelineEvent> timeline;
}

class OrderLine {
  const OrderLine({
    required this.id,
    required this.sku,
    required this.quantity,
    required this.unit,
    required this.unitPrice,
  });

  factory OrderLine.fromJson(JsonMap json) => OrderLine(
    id: jsonString(json['id'], 'id'),
    sku: jsonString(json['sku'], 'sku'),
    quantity: Decimal.parse(json['quantity'].toString()),
    unit: jsonString(json['unit'], 'unit'),
    unitPrice: Decimal.parse(json['unit_price'].toString()),
  );

  final String id;
  final String sku;
  final Decimal quantity;
  final String unit;
  final Decimal unitPrice;
}

class OrderTimelineEvent {
  const OrderTimelineEvent({
    required this.id,
    required this.status,
    required this.occurredAt,
  });

  factory OrderTimelineEvent.fromJson(JsonMap json) => OrderTimelineEvent(
    id: jsonString(json['id'], 'id'),
    status: jsonString(json['status'], 'status'),
    occurredAt: DateTime.parse(jsonString(json['occurred_at'], 'occurred_at')),
  );

  final String id;
  final String status;
  final DateTime occurredAt;
}
