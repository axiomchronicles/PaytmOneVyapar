import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/app_text_field.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class InventoryScreen extends ConsumerStatefulWidget {
  const InventoryScreen({super.key});

  @override
  ConsumerState<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends ConsumerState<InventoryScreen> {
  final _search = TextEditingController();

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final inventory = ref.watch(inventoryControllerProvider);
    final filtered = ref.watch(filteredInventoryProvider);
    return RefreshIndicator(
      onRefresh: ref.read(inventoryControllerProvider.notifier).refresh,
      child: CustomScrollView(
        key: const PageStorageKey('inventory_scroll'),
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          const SliverSection(child: SizedBox(height: AppSpacing.sm)),
          const SliverSection(
            child: AppHeader(
              title: 'Inventory',
              subtitle: 'Live stock from your selected store',
            ),
          ),
          const SliverSection(child: SizedBox(height: AppSpacing.lg)),
          SliverSection(
            child: AppSearchField(
              controller: _search,
              hint: 'Search by product or SKU',
              onChanged: ref.read(inventorySearchProvider.notifier).update,
            ),
          ),
          const SliverSection(child: SizedBox(height: AppSpacing.lg)),
          if (inventory.isLoading)
            const SliverSection(child: LoadingSkeleton(rows: 6))
          else if (inventory.hasError)
            SliverFillRemaining(
              hasScrollBody: false,
              child: AppErrorState(
                error: inventory.error!,
                onRetry: ref.read(inventoryControllerProvider.notifier).refresh,
              ),
            )
          else if (filtered.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: EmptyState(
                title: _search.text.isEmpty
                    ? 'No inventory yet'
                    : 'No matching inventory',
                message: _search.text.isEmpty
                    ? 'Inventory will appear after it is added to the backend.'
                    : 'Try a different product name or SKU.',
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              sliver: SliverList.separated(
                itemCount: filtered.length,
                separatorBuilder: (context, index) => const Divider(indent: 52),
                itemBuilder: (context, index) =>
                    InventoryRow(item: filtered[index]),
              ),
            ),
          const SliverPadding(padding: EdgeInsets.only(bottom: 110)),
        ],
      ),
    );
  }
}

class InventoryRow extends StatelessWidget {
  const InventoryRow({required this.item, super.key});

  final InventoryItem item;

  @override
  Widget build(BuildContext context) => ListTile(
    key: ValueKey('inventory_${item.inventoryId}'),
    minTileHeight: 74,
    contentPadding: const EdgeInsets.symmetric(vertical: 4),
    leading: Container(
      width: 42,
      height: 42,
      decoration: BoxDecoration(
        color: item.isLow ? AppColors.warningSurface : AppColors.paleBlue,
        shape: BoxShape.circle,
      ),
      child: Center(
        child: VyaparIcon(
          VyaparIcons.inventory,
          size: 21,
          color: item.isLow ? AppColors.warning : AppColors.blue,
        ),
      ),
    ),
    title: Text(item.name, maxLines: 1, overflow: TextOverflow.ellipsis),
    subtitle: Text(
      '${item.sku} · reorder at ${formatQuantity(item.reorderPoint)}',
    ),
    trailing: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(
          formatQuantity(item.quantityOnHand),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        Text(item.unit, style: Theme.of(context).textTheme.labelMedium),
      ],
    ),
    onTap: () => context.push('/inventory/${item.inventoryId}'),
  );
}
