import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/core/auth/auth_session.dart' as core;
import 'package:vyapar/design_system/theme/app_theme.dart';
import 'package:vyapar/features/analytics/models/analytics_overview.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/features/approvals/data/approval_repository.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/approvals/presentation/approval_detail_screen.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/features/auth/presentation/sign_in_screen.dart';
import 'package:vyapar/features/auth/presentation/welcome_screen.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/features/home/presentation/home_screen.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/presentation/inventory_screen.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/munim/presentation/munim_screen.dart';
import 'package:vyapar/features/orders/presentation/orders_screen.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';
import 'package:vyapar/features/recommendations/models/recommendation.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';
import 'package:vyapar/features/voice/models/voice_models.dart';
import 'package:vyapar/features/voice/presentation/voice_screen.dart';
import 'package:vyapar/features/voice/providers/voice_provider.dart';
import 'package:vyapar/l10n/app_localizations.dart';

class _AuthState extends AuthController {
  @override
  Future<core.AuthSession> build() async =>
      const core.AuthSession.unauthenticated();
}

class _MerchantState extends MerchantController {
  @override
  Future<MerchantProfile> build() async => merchant;
}

class _InventoryState extends InventoryController {
  @override
  Future<List<InventoryItem>> build() async => const [cola];
}

class _RecommendationState extends RecommendationController {
  @override
  Future<List<Recommendation>> build() async => const [recommendation];
}

class _AnalyticsState extends AnalyticsController {
  @override
  Future<AnalyticsOverview> build() async => analytics;
}

class _VoiceState extends VoiceController {
  @override
  VoiceState build() => const VoiceState();
}

class _ApprovalRepository extends ApprovalRepository {
  _ApprovalRepository() : super(Dio());

  @override
  Future<ApprovalDetail> get(String approvalId) async => approval;
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
  name: 'Cola 300 ml crate',
  unit: 'crate',
  quantityOnHand: 3,
  reorderPoint: 8,
  isLow: true,
);

const recommendation = Recommendation(sku: 'COLD-COLA-300', score: 0.76);

const analytics = AnalyticsOverview(
  salesQuantity: 371,
  lowInventoryProducts: 1,
  ordersByStatus: {'CONFIRMED': 1},
);

final approval = ApprovalDetail(
  id: 'approval-id',
  proposalId: 'proposal-id',
  orderHash: List<String>.filled(64, 'a').join(),
  proposal: ProposalDetail(
    proposalId: 'proposal-id',
    storeId: 'store-id',
    supplierId: 'supplier-id',
    sku: 'COLD-COLA-300',
    quantity: 5,
    unit: 'crate',
    unitPrice: 470,
    currency: 'INR',
    deliveryAt: DateTime(2026, 9, 20, 12),
    quoteId: 'quote-id',
  ),
  status: 'PENDING',
  expiresAt: DateTime(2026, 9, 18, 22),
  createdAt: DateTime(2026, 9, 18, 21),
);

Widget app(Widget child) => MaterialApp(
  debugShowCheckedModeBanner: false,
  theme: AppTheme.light,
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: child,
);

Future<void> expectGolden(
  WidgetTester tester,
  Widget widget,
  String name,
) async {
  await tester.binding.setSurfaceSize(const Size(390, 844));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(widget);
  await tester.pumpAndSettle();
  await expectLater(
    find.byType(MaterialApp),
    matchesGoldenFile('goldens/$name.png'),
  );
}

void main() {
  testWidgets('welcome golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(child: app(const WelcomeScreen())),
      'welcome',
    );
  });

  testWidgets('sign in golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(
        overrides: [authControllerProvider.overrideWith(_AuthState.new)],
        child: app(const SignInScreen()),
      ),
      'sign_in',
    );
  });

  testWidgets('home golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(
        overrides: [
          merchantControllerProvider.overrideWith(_MerchantState.new),
          inventoryControllerProvider.overrideWith(_InventoryState.new),
          recommendationControllerProvider.overrideWith(
            _RecommendationState.new,
          ),
          analyticsControllerProvider.overrideWith(_AnalyticsState.new),
        ],
        child: app(const Scaffold(body: HomeScreen())),
      ),
      'home',
    );
  });

  testWidgets('inventory golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(
        overrides: [
          inventoryControllerProvider.overrideWith(_InventoryState.new),
        ],
        child: app(const Scaffold(body: InventoryScreen())),
      ),
      'inventory',
    );
  });

  testWidgets('approval golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(
        overrides: [
          approvalRepositoryProvider.overrideWithValue(_ApprovalRepository()),
        ],
        child: app(const ApprovalDetailScreen(approvalId: 'approval-id')),
      ),
      'approval',
    );
  });

  testWidgets('munim golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(
        overrides: [
          inventoryControllerProvider.overrideWith(_InventoryState.new),
          recommendationControllerProvider.overrideWith(
            _RecommendationState.new,
          ),
        ],
        child: app(const Scaffold(body: MunimScreen())),
      ),
      'munim',
    );
  });

  testWidgets('voice golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(
        overrides: [voiceControllerProvider.overrideWith(_VoiceState.new)],
        child: app(const VoiceScreen()),
      ),
      'voice',
    );
  });

  testWidgets('orders golden', (tester) async {
    await expectGolden(
      tester,
      ProviderScope(child: app(const Scaffold(body: OrdersScreen()))),
      'orders',
    );
  });
}
