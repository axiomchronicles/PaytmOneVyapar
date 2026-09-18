import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/analytics/models/analytics_detail.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class AnalyticsDetailScreen extends ConsumerWidget {
  const AnalyticsDetailScreen({required this.metric, super.key});

  final AnalyticsMetric metric;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(analyticsDetailProvider(metric));
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: '${sentenceCase(metric.name)} analytics',
                  subtitle: 'Bounded backend aggregates',
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
                child: detail.when(
                  loading: () => const AnalyticsDetailSkeleton(),
                  error: (error, _) => AppErrorState(error: error),
                  data: (value) => value.points.isEmpty
                      ? const EmptyState(
                          title: 'No data in this range',
                          message: 'Recorded activity will appear here.',
                        )
                      : Column(
                          children: [
                            for (final point in value.points)
                              _MetricBar(
                                point: point,
                                max: value.points
                                    .map((item) => item.value)
                                    .reduce((a, b) => a > b ? a : b),
                                currency: metric != AnalyticsMetric.inventory,
                                onTap: point.entityId == null
                                    ? null
                                    : () => context.push(
                                        '/suppliers/${point.entityId}',
                                      ),
                              ),
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

class _MetricBar extends StatelessWidget {
  const _MetricBar({
    required this.point,
    required this.max,
    required this.currency,
    this.onTap,
  });

  final AnalyticsDatum point;
  final Decimal max;
  final bool currency;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(AppRadii.sm),
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(point.label)),
              Text(
                currency ? formatInr(point.value) : formatQuantity(point.value),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          FractionallySizedBox(
            widthFactor: max == Decimal.zero
                ? 0
                : point.value.toDouble() / max.toDouble(),
            child: Container(
              height: 8,
              decoration: BoxDecoration(
                color: AppColors.cyan,
                borderRadius: BorderRadius.circular(AppRadii.pill),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}
