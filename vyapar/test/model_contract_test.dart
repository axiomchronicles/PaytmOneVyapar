import 'package:decimal/decimal.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/core/networking/realtime_event.dart';
import 'package:vyapar/features/analytics/models/analytics_overview.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';

void main() {
  test('inventory maps decimal strings from FastAPI', () {
    final item = InventoryItem.fromJson({
      'inventory_id': 'inventory-id',
      'store_id': 'store-id',
      'product_id': 'product-id',
      'sku': 'COLD-COLA-300',
      'name': 'Cola crate',
      'unit': 'crate',
      'quantity_on_hand': '3.000',
      'reorder_point': '8.000',
      'is_low': true,
    });

    expect(item.quantityOnHand, 3);
    expect(item.reorderPoint, 8);
    expect(item.isLow, isTrue);
  });

  test('analytics maps status aggregates without inventing revenue', () {
    final overview = AnalyticsOverview.fromJson({
      'sales_quantity': '91.500',
      'low_inventory_products': 2,
      'orders_by_status': {'CONFIRMED': 3, 'FAILED': 1},
    });

    expect(overview.salesQuantity, 91.5);
    expect(overview.totalOrders, 4);
  });

  test('approval computes display total from canonical proposal fields', () {
    final approval = ApprovalDetail.fromJson({
      'id': 'approval-id',
      'proposal_id': 'proposal-id',
      'merchant_id': 'merchant-id',
      'order_hash': List<String>.filled(64, 'a').join(),
      'proposal': {
        'proposal_id': 'proposal-id',
        'merchant_id': 'merchant-id',
        'store_id': 'store-id',
        'supplier_id': 'supplier-id',
        'sku': 'COLD-COLA-300',
        'quantity': '5',
        'unit': 'crate',
        'unit_price': '1825',
        'currency': 'INR',
        'delivery_at': '2026-09-20T12:00:00+05:30',
        'quote_id': 'quote-id',
      },
      'status': 'PENDING',
      'expires_at': '2026-09-18T22:00:00+05:30',
      'created_at': '2026-09-18T21:00:00+05:30',
    });

    expect(approval.proposal.totalAmount, Decimal.fromInt(9125));
    expect(approval.isPending, isTrue);
  });

  test('order maps only backend status values', () {
    final order = OrderDetail.fromJson({
      'id': 'order-id',
      'proposal_id': 'proposal-id',
      'supplier_id': 'supplier-id',
      'status': 'CONFIRMED',
      'total_amount': '940.00',
      'currency': 'INR',
      'supplier_reference': 'BWW-123',
      'failure_reason': null,
      'created_at': '2026-09-18T10:00:00Z',
    });

    expect(order.status, 'CONFIRMED');
    expect(order.supplierReference, 'BWW-123');
  });

  test('malformed realtime event is rejected safely', () {
    expect(
      () => RealtimeEvent.fromJson(jsonMap({'data': <String, Object?>{}})),
      throwsFormatException,
    );
  });
}
