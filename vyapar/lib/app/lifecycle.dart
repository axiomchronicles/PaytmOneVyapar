import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/core/networking/realtime_provider.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/orders/providers/order_provider.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';

class AppLifecycle extends ConsumerWidget {
  const AppLifecycle({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.listen(realtimeEventsProvider, (previous, next) {
      next.whenData((event) {
        switch (event.type) {
          case 'INVENTORY_LOW':
          case 'DEMAND_SURGE_DETECTED':
            ref.invalidate(inventoryControllerProvider);
            ref.invalidate(recommendationControllerProvider);
            ref.invalidate(analyticsControllerProvider);
          case 'APPROVAL_REQUIRED':
          case 'APPROVAL_GRANTED':
          case 'APPROVAL_REJECTED':
            ref.invalidate(approvalControllerProvider);
          case 'ORDER_EXECUTED':
          case 'ORDER_FAILED':
          case 'SUPPLIER_CONFIRMATION_RECEIVED':
            ref.invalidate(orderDetailProvider);
            ref.invalidate(analyticsControllerProvider);
        }
      });
    });
    return child;
  }
}
