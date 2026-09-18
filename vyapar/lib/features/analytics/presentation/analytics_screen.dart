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
import 'package:vyapar/features/analytics/models/analytics_detail.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class AnalyticsScreen extends ConsumerWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analytics = ref.watch(analyticsControllerProvider);
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Business overview',
                  subtitle: 'Backend aggregates across your business',
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
                child: analytics.when(
                  loading: () => const AnalyticsScreenSkeleton(),
                  error: (error, _) => AppErrorState(
                    error: error,
                    onRetry: ref
                        .read(analyticsControllerProvider.notifier)
                        .refresh,
                  ),
                  data: (value) => Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: AppSpacing.lg),
                      Text(
                        formatQuantity(value.salesQuantity),
                        style: Theme.of(context).textTheme.displaySmall
                            ?.copyWith(color: AppColors.navy),
                      ),
                      const Text('Units sold across recorded sales'),
                      const SizedBox(height: AppSpacing.xl),
                      const SectionHeader(title: 'Operational totals'),
                      const SizedBox(height: AppSpacing.md),
                      MetricTile(
                        value: '${value.lowInventoryProducts}',
                        label: 'Products at or below reorder point',
                        accent: value.lowInventoryProducts > 0
                            ? AppColors.warning
                            : AppColors.success,
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      for (final metric in AnalyticsMetric.values)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text('${sentenceCase(metric.name)} analytics'),
                          trailing: const VyaparIcon(
                            VyaparIcons.forward,
                            size: 18,
                          ),
                          onTap: () =>
                              context.push('/analytics/${metric.name}'),
                        ),
                      const SizedBox(height: AppSpacing.sm),
                      MetricTile(
                        value: '${value.totalOrders}',
                        label: 'Orders across all statuses',
                      ),
                      const SizedBox(height: AppSpacing.xl),
                      const SectionHeader(title: 'Orders by status'),
                      const SizedBox(height: AppSpacing.sm),
                      if (value.ordersByStatus.isEmpty)
                        const EmptyState(
                          title: 'No orders recorded',
                          message:
                              'Order totals will appear after purchases are approved.',
                        )
                      else
                        for (final entry in value.ordersByStatus.entries)
                          _StatusCount(status: entry.key, count: entry.value),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusCount extends StatelessWidget {
  const _StatusCount({required this.status, required this.count});

  final String status;
  final int count;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 11),
    child: Row(
      children: [
        Expanded(child: Text(sentenceCase(status))),
        Text('$count', style: Theme.of(context).textTheme.titleMedium),
      ],
    ),
  );
}
