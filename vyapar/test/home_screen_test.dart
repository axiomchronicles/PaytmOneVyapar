import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/features/analytics/models/analytics_overview.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/features/home/presentation/home_screen.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';
import 'package:vyapar/features/recommendations/models/recommendation.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';

class _MerchantState extends MerchantController {
  _MerchantState(this.value);
  final MerchantProfile value;
  @override
  Future<MerchantProfile> build() async => value;
}

class _InventoryState extends InventoryController {
  _InventoryState(this.value);
  final List<InventoryItem> value;
  @override
  Future<List<InventoryItem>> build() async => value;
}

class _RecommendationState extends RecommendationController {
  _RecommendationState(this.value);
  final List<Recommendation> value;
  @override
  Future<List<Recommendation>> build() async => value;
}

class _AnalyticsState extends AnalyticsController {
  _AnalyticsState(this.value);
  final AnalyticsOverview value;
  @override
  Future<AnalyticsOverview> build() async => value;
}

class _PendingInventoryState extends InventoryController {
  @override
  Future<List<InventoryItem>> build() =>
      Completer<List<InventoryItem>>().future;
}

class _FailingRecommendationState extends RecommendationController {
  @override
  Future<List<Recommendation>> build() =>
      throw StateError('recommendations failed');
}

const merchant = MerchantProfile(
  id: 'merchant-id',
  name: 'Sharma General Store',
  currency: 'INR',
  spendingLimit: 50000,
  stores: [StoreSummary(id: 'store-id', name: 'Main Store')],
);

const cola = InventoryItem(
  inventoryId: 'inventory-id',
  storeId: 'store-id',
  productId: 'product-id',
  sku: 'COLD-COLA-300',
  name: 'Cola crate',
  unit: 'crate',
  quantityOnHand: 3,
  reorderPoint: 8,
  isLow: true,
);

const analytics = AnalyticsOverview(
  salesQuantity: 90,
  lowInventoryProducts: 1,
  ordersByStatus: {'CONFIRMED': 2},
);

Widget homeWith({
  List<InventoryItem> inventory = const [cola],
  List<Recommendation> recommendations = const [
    Recommendation(sku: 'COLD-COLA-300', score: 0.9),
  ],
  bool pendingInventory = false,
  bool recommendationError = false,
}) => ProviderScope(
  overrides: [
    merchantControllerProvider.overrideWith(() => _MerchantState(merchant)),
    inventoryControllerProvider.overrideWith(
      () => pendingInventory
          ? _PendingInventoryState()
          : _InventoryState(inventory),
    ),
    recommendationControllerProvider.overrideWith(
      () => recommendationError
          ? _FailingRecommendationState()
          : _RecommendationState(recommendations),
    ),
    analyticsControllerProvider.overrideWith(() => _AnalyticsState(analytics)),
  ],
  child: const MaterialApp(home: Scaffold(body: HomeScreen())),
);

void main() {
  testWidgets('home renders live merchant metrics and signals', (tester) async {
    await tester.pumpWidget(homeWith());
    await tester.pumpAndSettle();

    expect(find.text('Sharma General Store'), findsOneWidget);
    expect(find.text('1 inventory item needs attention.'), findsOneWidget);
    await tester.drag(find.byType(CustomScrollView), const Offset(0, -500));
    await tester.pumpAndSettle();
    expect(find.text('COLD-COLA-300'), findsOneWidget);
  });

  testWidgets('home renders honest empty recommendation state', (tester) async {
    await tester.pumpWidget(
      homeWith(inventory: const [], recommendations: const []),
    );
    await tester.pumpAndSettle();

    await tester.drag(find.byType(CustomScrollView), const Offset(0, -600));
    await tester.pumpAndSettle();
    expect(find.text('No new recommendations'), findsOneWidget);
  });

  testWidgets('home renders loading geometry', (tester) async {
    await tester.pumpWidget(homeWith(pendingInventory: true));
    await tester.pump();

    expect(find.text('Checking your shop now…'), findsOneWidget);
  });

  testWidgets('home renders recommendation error state', (tester) async {
    await tester.pumpWidget(homeWith(recommendationError: true));
    await tester.pumpAndSettle();

    await tester.drag(find.byType(CustomScrollView), const Offset(0, -600));
    await tester.pumpAndSettle();
    expect(find.text('Couldn’t load this'), findsOneWidget);
  });
}
