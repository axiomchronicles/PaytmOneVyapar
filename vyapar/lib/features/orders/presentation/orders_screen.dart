import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';
import 'package:vyapar/features/orders/providers/order_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class OrdersScreen extends ConsumerWidget {
  const OrdersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orders = ref.watch(orderListProvider);
    return RefreshIndicator(
      onRefresh: ref.read(orderListProvider.notifier).refresh,
      child: CustomScrollView(
        key: const PageStorageKey('orders_scroll'),
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          const SliverPadding(
            padding: EdgeInsets.all(AppSpacing.md),
            sliver: SliverToBoxAdapter(
              child: AppHeader(
                title: 'Orders',
                subtitle: 'Live procurement orders and status',
              ),
            ),
          ),
          orders.when(
            loading: () => const SliverSection(child: ListSkeleton(rows: 6)),
            error: (error, _) => SliverFillRemaining(
              hasScrollBody: false,
              child: AppErrorState(
                error: error,
                onRetry: ref.read(orderListProvider.notifier).refresh,
              ),
            ),
            data: (page) => page.items.isEmpty
                ? const SliverFillRemaining(
                    hasScrollBody: false,
                    child: EmptyState(
                      title: 'No orders yet',
                      message: 'Approved purchases will appear here.',
                    ),
                  )
                : SliverPadding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.md,
                    ),
                    sliver: SliverList.separated(
                      itemCount: page.items.length + (page.hasMore ? 1 : 0),
                      separatorBuilder: (_, _) => const Divider(indent: 52),
                      itemBuilder: (context, index) {
                        if (index == page.items.length) {
                          ref.read(orderListProvider.notifier).loadMore();
                          return const Padding(
                            padding: EdgeInsets.all(AppSpacing.md),
                            child: Center(child: CircularProgressIndicator()),
                          );
                        }
                        return _OrderRow(order: page.items[index]);
                      },
                    ),
                  ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 110)),
        ],
      ),
    );
  }
}

class _OrderRow extends StatelessWidget {
  const _OrderRow({required this.order});

  final OrderDetail order;

  @override
  Widget build(BuildContext context) => ListTile(
    key: ValueKey('order_${order.id}'),
    contentPadding: EdgeInsets.zero,
    minTileHeight: 76,
    leading: const VyaparIcon(VyaparIcons.orders, color: AppColors.blue),
    title: Text(order.supplierName),
    subtitle: Text(
      '${formatInr(order.totalAmount)} · ${formatDateTime(order.createdAt)}',
    ),
    trailing: StatusPill(label: sentenceCase(order.status)),
    onTap: () => context.push('/order/${order.id}'),
  );
}
