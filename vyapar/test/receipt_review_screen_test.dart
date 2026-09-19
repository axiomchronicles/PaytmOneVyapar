import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/features/inventory/models/receipt_scan.dart';
import 'package:vyapar/features/inventory/presentation/manual_inventory_screen.dart';
import 'package:vyapar/features/inventory/presentation/receipt_review_screen.dart';
import 'package:vyapar/features/inventory/providers/receipt_scan_provider.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';

class _ReceiptState extends ReceiptScanController {
  @override
  ReceiptScanState build() => ReceiptScanState(review: _review());
}

class _MerchantState extends MerchantController {
  @override
  Future<MerchantProfile> build() async => const MerchantProfile(
    id: 'merchant-id',
    name: 'Test Store',
    currency: 'INR',
    spendingLimit: 50000,
    stores: [
      StoreSummary(
        id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
        name: 'Main Store',
      ),
    ],
  );
}

Map<String, double> _confidence() => {
  for (final field in receiptItemFields) field: field == 'unit' ? 0.6 : 0.95,
};

ReceiptScanReview _review() => ReceiptScanReview(
  scanId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  receipt: ReceiptMetadata(
    values: {for (final field in receiptHeaderFields) field: null},
    fieldConfidence: {for (final field in receiptHeaderFields) field: 0},
  ),
  items: [
    ReceiptReviewItem(
      lineId: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      values: {
        for (final field in receiptItemFields)
          field: switch (field) {
            'name' => 'Tata Salt 1kg',
            'quantity' => '10',
            'unit' => 'piece',
            'unit_price' => '28',
            _ => null,
          },
      },
      confidence: 0.91,
      fieldConfidence: _confidence(),
      missingFields: const {'sku'},
      lowConfidenceFields: const {'unit'},
      sourceFields: const {'name', 'quantity', 'unit', 'unit_price'},
      editedFields: const {},
      sourceText: 'Tata Salt 1kg 10 28',
    ),
  ],
  detectedItems: 1,
  warnings: const [],
  imagePreprocessed: false,
);

void main() {
  testWidgets('manual inventory initializes after route build', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          merchantControllerProvider.overrideWith(_MerchantState.new),
        ],
        child: const MaterialApp(home: ManualInventoryScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Add inventory', skipOffstage: false), findsOneWidget);
    expect(find.text('Save inventory', skipOffstage: false), findsOneWidget);
  });

  testWidgets('review screen exposes provenance and preserves merchant edits', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          receiptScanControllerProvider.overrideWith(_ReceiptState.new),
          merchantControllerProvider.overrideWith(_MerchantState.new),
        ],
        child: const MaterialApp(home: ReceiptReviewScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('1 products detected', skipOffstage: false),
      findsOneWidget,
    );
    expect(find.text('Tata Salt 1kg', skipOffstage: false), findsWidgets);
    expect(
      find.text('Required · not found', skipOffstage: false),
      findsWidgets,
    );
    expect(
      find.textContaining('Please check', skipOffstage: false),
      findsWidgets,
    );

    final skuField = find.byKey(
      const ValueKey('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb_sku'),
      skipOffstage: false,
    );
    await tester.scrollUntilVisible(skuField, 300);
    await tester.pump();
    await tester.enterText(skuField, 'SALT-TATA-1KG');
    await tester.pump();
    expect(find.text('Edited by you', skipOffstage: false), findsWidgets);

    final addButton = find.byKey(
      const ValueKey('add_receipt_item'),
      skipOffstage: false,
    );
    tester.widget<SecondaryButton>(addButton).onPressed!();
    await tester.pump();
    final container = ProviderScope.containerOf(
      tester.element(find.byType(ReceiptReviewScreen)),
    );
    expect(
      container.read(receiptScanControllerProvider).review?.items,
      hasLength(2),
    );
  });
}
