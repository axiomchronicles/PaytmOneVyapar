import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/features/inventory/models/receipt_scan.dart';

Map<String, double> confidence({double value = 0}) => {
  for (final field in receiptItemFields) field: value,
};

Map<String, Object?> reviewJson() => {
  'scan_id': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'status': 'review_required',
  'receipt': {
    'supplier_name': null,
    'invoice_number': 'INV-1',
    'invoice_date': null,
    'currency': 'INR',
    'subtotal': null,
    'tax': null,
    'total': '280.00',
    'field_confidence': {
      for (final field in receiptHeaderFields)
        field: field == 'total' ? 0.95 : 0,
    },
    'source_text': 'INV-1 Total 280',
  },
  'items': [
    {
      'line_id': 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'name': 'Tata Salt 1kg',
      'sku': null,
      'barcode': null,
      'category': null,
      'brand': 'Tata',
      'description': null,
      'quantity': '10.000',
      'unit': 'piece',
      'unit_price': '28.00',
      'purchase_price': null,
      'selling_price': null,
      'mrp': null,
      'gst_rate': null,
      'tax_amount': null,
      'discount': null,
      'total_amount': '280.00',
      'expiry_date': null,
      'batch_number': null,
      'confidence': 0.91,
      'field_confidence': {
        ...confidence(),
        'name': 0.99,
        'quantity': 0.97,
        'unit': 0.7,
        'unit_price': 0.95,
        'total_amount': 0.98,
      },
      'source_text': 'Tata Salt 1kg 10 28 280',
      'missing_fields': ['sku', 'barcode'],
      'low_confidence_fields': ['unit'],
      'source_fields': [
        'name',
        'quantity',
        'unit',
        'unit_price',
        'total_amount',
      ],
      'matched_product_id': null,
      'match_type': null,
    },
  ],
  'detected_items': 1,
  'warnings': [],
  'image_preprocessed': false,
};

void main() {
  test('receipt review preserves missing and uncertain field provenance', () {
    final review = ReceiptScanReview.fromJson(reviewJson());
    final item = review.items.single;

    expect(item.status('name'), ReceiptFieldStatus.scanned);
    expect(item.status('unit'), ReceiptFieldStatus.uncertain);
    expect(item.status('sku'), ReceiptFieldStatus.missing);
    expect(item.isReady, isFalse);

    final edited = item.update('sku', 'SALT-TATA-1KG');
    expect(edited.status('sku'), ReceiptFieldStatus.edited);
    expect(edited.isReady, isTrue);
    expect(edited.toConfirmJson()['edited_fields'], contains('sku'));
    expect(edited.toConfirmJson(), isNot(contains('missing_fields')));
  });

  test('manual receipt item starts empty and requires merchant completion', () {
    final item = ReceiptReviewItem.manual();
    expect(item.isReady, isFalse);
    expect(item.status('name'), ReceiptFieldStatus.missing);
    expect(item.sourceFields, isEmpty);
  });
}
