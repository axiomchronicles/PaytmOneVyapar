import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';
import 'package:vyapar/features/orders/providers/order_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class OrderDetailScreen extends ConsumerWidget {
  const OrderDetailScreen({required this.orderId, super.key});

  final String orderId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final order = ref.watch(orderDetailProvider(orderId));
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Order detail',
                  subtitle: orderId,
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: order.when(
                  loading: () => const OrderDetailSkeleton(),
                  error: (error, _) => AppErrorState(
                    error: error,
                    onRetry: () => ref.invalidate(orderDetailProvider(orderId)),
                  ),
                  data: (value) => _OrderBody(order: value),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OrderBody extends StatelessWidget {
  const _OrderBody({required this.order});

  final OrderDetail order;

  @override
  Widget build(BuildContext context) {
    final success = order.status == 'CONFIRMED';
    final failed = order.status == 'FAILED' || order.status == 'CANCELLED';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: AppSpacing.lg),
        StatusPill(
          label: sentenceCase(order.status),
          tone: success
              ? StatusTone.success
              : failed
              ? StatusTone.danger
              : StatusTone.info,
        ),
        const SizedBox(height: AppSpacing.md),
        AmountText(amount: order.totalAmount, label: 'Order total'),
        const SizedBox(height: AppSpacing.xl),
        const Divider(),
        const SizedBox(height: AppSpacing.lg),
        Text('Progress', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: AppSpacing.md),
        AppTimeline(
          items: order.timeline.isEmpty
              ? [
                  TimelineItem(
                    title: sentenceCase(order.status),
                    complete: true,
                  ),
                ]
              : [
                  for (final event in order.timeline)
                    TimelineItem(
                      title: sentenceCase(event.status),
                      subtitle: formatDateTime(event.occurredAt),
                      complete: true,
                    ),
                ],
        ),
        if (order.supplierReference case final reference?) ...[
          const Divider(),
          const SizedBox(height: AppSpacing.md),
          Text(
            'Supplier confirmation',
            style: Theme.of(context).textTheme.labelMedium,
          ),
          const SizedBox(height: AppSpacing.xs),
          SelectableText(
            reference,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
        if (order.failureReason case final reason?) ...[
          const SizedBox(height: AppSpacing.lg),
          Text(
            reason,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.danger),
          ),
        ],
        const SizedBox(height: AppSpacing.xl),
        Text(
          'Created ${formatDateTime(order.createdAt)}',
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
        ),
      ],
    );
  }
}
