import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/core/networking/realtime_provider.dart';
import 'package:vyapar/core/networking/realtime_router.dart';
import 'package:vyapar/features/activity/providers/activity_provider.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';
import 'package:vyapar/features/notifications/providers/notification_provider.dart';
import 'package:vyapar/features/orders/providers/order_provider.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';
import 'package:vyapar/features/suppliers/providers/supplier_provider.dart';

class AppLifecycle extends ConsumerStatefulWidget {
  const AppLifecycle({required this.child, super.key});

  final Widget child;

  @override
  ConsumerState<AppLifecycle> createState() => _AppLifecycleState();
}

class _AppLifecycleState extends ConsumerState<AppLifecycle> {
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();
    _lifecycle = AppLifecycleListener(
      onResume: () =>
          ref.read(realtimeForegroundProvider.notifier).setForeground(true),
      onPause: () =>
          ref.read(realtimeForegroundProvider.notifier).setForeground(false),
      onDetach: () =>
          ref.read(realtimeForegroundProvider.notifier).setForeground(false),
    );
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    super.dispose();
  }

  void _invalidateAll() {
    ref.invalidate(inventoryControllerProvider);
    ref.invalidate(recommendationControllerProvider);
    ref.invalidate(analyticsControllerProvider);
    ref.invalidate(approvalListProvider);
    ref.invalidate(orderListProvider);
    ref.invalidate(supplierListProvider);
    ref.invalidate(negotiationListProvider);
    ref.invalidate(a2aActivityProvider);
    ref.invalidate(businessActivityProvider);
    ref.invalidate(notificationListProvider);
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(realtimeEventsProvider, (previous, next) {
      next.whenData((event) {
        final targets = RealtimeEventRouter.targets(event.type);
        if (targets.contains(RealtimeTarget.auth)) {
          unawaited(ref.read(authControllerProvider.notifier).signOut());
        }
        if (targets.contains(RealtimeTarget.all)) _invalidateAll();
        if (targets.contains(RealtimeTarget.inventory)) {
          ref.invalidate(inventoryControllerProvider);
        }
        if (targets.contains(RealtimeTarget.recommendations)) {
          ref.invalidate(recommendationControllerProvider);
        }
        if (targets.contains(RealtimeTarget.analytics)) {
          ref.invalidate(analyticsControllerProvider);
        }
        if (targets.contains(RealtimeTarget.approvals)) {
          ref.invalidate(approvalControllerProvider);
          ref.invalidate(approvalListProvider);
        }
        if (targets.contains(RealtimeTarget.orders)) {
          ref.invalidate(orderDetailProvider);
          ref.invalidate(orderListProvider);
        }
        if (targets.contains(RealtimeTarget.suppliers)) {
          ref.invalidate(supplierListProvider);
        }
        if (targets.contains(RealtimeTarget.negotiations)) {
          ref.invalidate(negotiationListProvider);
        }
        if (targets.contains(RealtimeTarget.a2a)) {
          ref.invalidate(a2aActivityProvider);
        }
        if (targets.contains(RealtimeTarget.notifications)) {
          ref.invalidate(notificationListProvider);
        }
      });
    });
    return widget.child;
  }
}
