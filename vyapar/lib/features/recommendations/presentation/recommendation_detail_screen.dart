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
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class RecommendationDetailScreen extends ConsumerWidget {
  const RecommendationDetailScreen({required this.sku, super.key});

  final String sku;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendation = ref.watch(recommendationDetailProvider(sku));
    final inventory = ref.watch(inventoryControllerProvider);
    InventoryItem? stock;
    for (final item in inventory.value ?? const <InventoryItem>[]) {
      if (item.sku == sku) {
        stock = item;
        break;
      }
    }
    if (recommendation == null &&
        (ref.watch(recommendationControllerProvider).isLoading ||
            inventory.isLoading)) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Recommendation',
                  subtitle: sku,
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
                child: recommendation == null
                    ? const EmptyState(
                        title: 'Recommendation not found',
                        message:
                            'Refresh the recommendation list and try again.',
                      )
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: AppSpacing.lg),
                          const StatusPill(
                            label: 'RECOMMENDATION',
                            tone: StatusTone.info,
                          ),
                          const SizedBox(height: AppSpacing.md),
                          Text(
                            sku,
                            style: Theme.of(context).textTheme.headlineLarge,
                          ),
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            'Priority score ${recommendation.score.toStringAsFixed(2)}',
                            style: Theme.of(context).textTheme.bodyLarge
                                ?.copyWith(color: AppColors.muted),
                          ),
                          if (stock != null) ...[
                            const SizedBox(height: AppSpacing.xl),
                            const Divider(),
                            const SizedBox(height: AppSpacing.md),
                            _Fact(
                              label: 'Current stock',
                              value:
                                  '${formatQuantity(stock.quantityOnHand)} ${stock.unit}',
                            ),
                            _Fact(
                              label: 'Reorder point',
                              value:
                                  '${formatQuantity(stock.reorderPoint)} ${stock.unit}',
                            ),
                            _Fact(
                              label: 'Stock signal',
                              value: stock.isLow
                                  ? 'Below reorder point'
                                  : 'Above reorder point',
                            ),
                          ],
                          const SizedBox(height: AppSpacing.xl),
                          Text(
                            'The backend does not provide a forecast, reason, suggested quantity, or supplier context for this recommendation. No purchase action is shown until those inputs are authoritative.',
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(color: AppColors.muted),
                          ),
                        ],
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 10),
    child: Row(
      children: [
        Expanded(child: Text(label)),
        Text(value, style: Theme.of(context).textTheme.titleMedium),
      ],
    ),
  );
}
