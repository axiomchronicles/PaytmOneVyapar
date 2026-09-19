import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/app/app.dart';
import 'package:vyapar/app/router.dart';
import 'package:vyapar/core/auth/auth_session.dart';
import 'package:vyapar/core/networking/realtime_event.dart';
import 'package:vyapar/core/networking/realtime_provider.dart';
import 'package:vyapar/features/analytics/models/analytics_overview.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';
import 'package:vyapar/features/recommendations/models/recommendation.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';

class _AuthState extends AuthController {
  _AuthState(this.value);
  final AuthSession value;
  @override
  Future<AuthSession> build() async => value;
}

class _MerchantState extends MerchantController {
  @override
  Future<MerchantProfile> build() async => const MerchantProfile(
    id: 'merchant-id',
    name: 'Test Merchant',
    currency: 'INR',
    spendingLimit: 1000,
    stores: [],
  );
}

class _InventoryState extends InventoryController {
  @override
  Future<List<InventoryItem>> build() async => const [];
}

class _RecommendationState extends RecommendationController {
  @override
  Future<List<Recommendation>> build() async => const [];
}

class _AnalyticsState extends AnalyticsController {
  @override
  Future<AnalyticsOverview> build() async => const AnalyticsOverview(
    salesQuantity: 0,
    lowInventoryProducts: 0,
    ordersByStatus: {},
  );
}

void main() {
  testWidgets(
    'unauthenticated launch redirects without flashing the app shell',
    (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              () => _AuthState(const AuthSession.unauthenticated()),
            ),
            realtimeEventsProvider.overrideWith(
              (ref) => const Stream<RealtimeEvent>.empty(),
            ),
            merchantControllerProvider.overrideWith(_MerchantState.new),
            inventoryControllerProvider.overrideWith(_InventoryState.new),
            recommendationControllerProvider.overrideWith(
              _RecommendationState.new,
            ),
            analyticsControllerProvider.overrideWith(_AnalyticsState.new),
          ],
          child: const VyaparApp(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('Your business, one step ahead'), findsOneWidget);
      expect(find.text('Home'), findsNothing);
    },
  );

  testWidgets('authenticated launch redirects to dashboard', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authControllerProvider.overrideWith(
            () => _AuthState(const AuthSession.authenticated()),
          ),
          realtimeEventsProvider.overrideWith(
            (ref) => const Stream<RealtimeEvent>.empty(),
          ),
          merchantControllerProvider.overrideWith(_MerchantState.new),
          inventoryControllerProvider.overrideWith(_InventoryState.new),
          recommendationControllerProvider.overrideWith(
            _RecommendationState.new,
          ),
          analyticsControllerProvider.overrideWith(_AnalyticsState.new),
        ],
        child: const VyaparApp(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Test Merchant'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) => widget is NavigationBar || widget is NavigationRail,
      ),
      findsOneWidget,
    );
  });

  testWidgets(
    'unauthenticated user can access /register/supplier without being bounced to welcome',
    (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              () => _AuthState(const AuthSession.unauthenticated()),
            ),
            realtimeEventsProvider.overrideWith(
              (ref) => const Stream<RealtimeEvent>.empty(),
            ),
            merchantControllerProvider.overrideWith(_MerchantState.new),
            inventoryControllerProvider.overrideWith(_InventoryState.new),
            recommendationControllerProvider.overrideWith(
              _RecommendationState.new,
            ),
            analyticsControllerProvider.overrideWith(_AnalyticsState.new),
          ],
          child: const VyaparApp(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      final context = tester.element(find.byType(VyaparApp));
      final router = ProviderScope.containerOf(context).read(appRouterProvider);

      router.go('/register/supplier');
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pump(const Duration(milliseconds: 500));

      expect(router.state.uri.toString(), '/register/supplier');
      expect(find.text('Your business, one step ahead'), findsNothing);
      expect(find.textContaining('wholesale supplier'), findsWidgets);
    },
  );

  testWidgets(
    'authenticated supplier is redirected to /supplier-home when opening /register/supplier',
    (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              () => _AuthState(
                const AuthSession.authenticated(
                  role: 'supplier',
                  accountType: 'supplier',
                  businessName: 'Metro Wholesale',
                ),
              ),
            ),
            realtimeEventsProvider.overrideWith(
              (ref) => const Stream<RealtimeEvent>.empty(),
            ),
            merchantControllerProvider.overrideWith(_MerchantState.new),
            inventoryControllerProvider.overrideWith(_InventoryState.new),
            recommendationControllerProvider.overrideWith(
              _RecommendationState.new,
            ),
            analyticsControllerProvider.overrideWith(_AnalyticsState.new),
          ],
          child: const VyaparApp(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      final context = tester.element(find.byType(VyaparApp));
      final router = ProviderScope.containerOf(context).read(appRouterProvider);

      router.go('/register/supplier');
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('SUPPLIER'), findsOneWidget);
    },
  );
}
