import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  final _orderId = TextEditingController();

  @override
  void dispose() {
    _orderId.dispose();
    super.dispose();
  }

  void _openOrder() {
    final value = _orderId.text.trim();
    if (value.isNotEmpty) context.push('/order/$value');
  }

  @override
  Widget build(BuildContext context) => CustomScrollView(
    key: const PageStorageKey('orders_scroll'),
    slivers: [
      const SliverPadding(
        padding: EdgeInsets.all(AppSpacing.md),
        sliver: SliverToBoxAdapter(
          child: AppHeader(
            title: 'Orders',
            subtitle: 'Open an order from a trusted Vyapar link',
          ),
        ),
      ),
      SliverToBoxAdapter(
        child: AdaptivePadding(
          child: Column(
            children: [
              const SizedBox(height: AppSpacing.xl),
              const EmptyState(
                title: 'Order list unavailable',
                message:
                    'The backend currently supports order lookup by ID but does not expose an order list.',
              ),
              TextField(
                key: const ValueKey('order_id_field'),
                controller: _orderId,
                textInputAction: TextInputAction.go,
                onSubmitted: (_) => _openOrder(),
                decoration: const InputDecoration(labelText: 'Order ID'),
              ),
              const SizedBox(height: AppSpacing.md),
              PrimaryButton(label: 'Open order', onPressed: _openOrder),
              const SizedBox(height: 110),
            ],
          ),
        ),
      ),
    ],
  );
}
