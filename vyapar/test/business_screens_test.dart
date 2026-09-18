import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/design_system/theme/app_theme.dart';
import 'package:vyapar/features/activity/models/activity.dart';
import 'package:vyapar/features/activity/presentation/activity_screen.dart';
import 'package:vyapar/features/activity/providers/activity_provider.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/approvals/presentation/approvals_screen.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/features/negotiations/models/negotiation.dart';
import 'package:vyapar/features/negotiations/presentation/negotiations_screen.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';
import 'package:vyapar/features/notifications/models/notification_item.dart';
import 'package:vyapar/features/notifications/presentation/notifications_screen.dart';
import 'package:vyapar/features/notifications/providers/notification_provider.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';
import 'package:vyapar/features/orders/presentation/orders_screen.dart';
import 'package:vyapar/features/orders/providers/order_provider.dart';
import 'package:vyapar/features/suppliers/models/supplier.dart';
import 'package:vyapar/features/suppliers/presentation/suppliers_screen.dart';
import 'package:vyapar/features/suppliers/providers/supplier_provider.dart';

class _Approvals extends ApprovalListController {
  @override
  Future<CursorPage<ApprovalDetail>> build() async =>
      const CursorPage(items: []);
}

class _Orders extends OrderListController {
  @override
  Future<CursorPage<OrderDetail>> build() async => const CursorPage(items: []);
}

class _Suppliers extends SupplierListController {
  @override
  Future<CursorPage<SupplierDetail>> build() async =>
      const CursorPage(items: []);
}

class _Negotiations extends NegotiationListController {
  @override
  Future<CursorPage<NegotiationDetail>> build() async =>
      const CursorPage(items: []);
}

class _Notifications extends NotificationListController {
  @override
  Future<CursorPage<NotificationItem>> build() async =>
      const CursorPage(items: []);
}

class _A2A extends A2AActivityController {
  @override
  Future<CursorPage<ActivityItem>> build() async => const CursorPage(items: []);
}

Widget _app(Widget child) => MaterialApp(theme: AppTheme.light, home: child);

void main() {
  testWidgets('backend-backed business lists expose honest empty states', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [approvalListProvider.overrideWith(_Approvals.new)],
        child: _app(const ApprovalsScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No approvals'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [orderListProvider.overrideWith(_Orders.new)],
        child: _app(const Scaffold(body: OrdersScreen())),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No orders yet'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [supplierListProvider.overrideWith(_Suppliers.new)],
        child: _app(const SuppliersScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No suppliers'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [negotiationListProvider.overrideWith(_Negotiations.new)],
        child: _app(const NegotiationsScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No negotiations yet'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [notificationListProvider.overrideWith(_Notifications.new)],
        child: _app(const NotificationsScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('You’re all caught up'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [a2aActivityProvider.overrideWith(_A2A.new)],
        child: _app(const ActivityScreen(a2a: true)),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No activity yet'), findsOneWidget);
  });
}
