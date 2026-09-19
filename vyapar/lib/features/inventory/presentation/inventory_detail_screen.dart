import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/app_sheet.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class InventoryDetailScreen extends ConsumerWidget {
  const InventoryDetailScreen({required this.inventoryId, super.key});

  final String inventoryId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(inventoryControllerProvider);
    final item = ref.watch(inventoryDetailProvider(inventoryId));
    return Scaffold(
      body: SafeArea(
        child: switch ((list.isLoading, list.hasError, item)) {
          (true, _, _) => const InventoryDetailSkeleton(),
          (_, true, _) => AppErrorState(
            error: list.error!,
            onRetry: ref.read(inventoryControllerProvider.notifier).refresh,
          ),
          (_, _, null) => const EmptyState(
            title: 'Inventory item not found',
            message: 'It may have changed since this page was opened.',
          ),
          (_, _, final value?) => _InventoryDetailBody(item: value),
        },
      ),
    );
  }
}

class _InventoryDetailBody extends ConsumerWidget {
  const _InventoryDetailBody({required this.item});

  final InventoryItem item;

  Future<void> _record(BuildContext context, WidgetRef ref) async {
    final change = await showAppSheet<double>(
      context: context,
      child: _StockAdjustmentSheet(item: item),
    );
    if (change == null || !context.mounted) return;
    try {
      await ref
          .read(inventoryControllerProvider.notifier)
          .recordAdjustment(
            item: item,
            quantityDelta: change,
            eventType: 'STOCK_RECEIVED',
            idempotencyKey: const Uuid().v4(),
          );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Stock updated from the backend.')),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => CustomScrollView(
    slivers: [
      SliverPadding(
        padding: const EdgeInsets.all(AppSpacing.md),
        sliver: SliverToBoxAdapter(
          child: AppHeader(
            title: item.name,
            subtitle: item.sku,
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: AppSpacing.lg),
              Text(
                formatQuantity(item.quantityOnHand),
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  color: item.isLow ? AppColors.warning : AppColors.navy,
                ),
              ),
              Text('${item.unit} on hand'),
              const SizedBox(height: AppSpacing.lg),
              const Divider(),
              const SizedBox(height: AppSpacing.md),
              _DetailLine(
                label: 'Reorder point',
                value: formatQuantity(item.reorderPoint),
              ),
              _DetailLine(
                label: 'Stock health',
                value: item.isLow ? 'Needs attention' : 'Healthy',
              ),
              if (item.category case final value?)
                _DetailLine(label: 'Category', value: value),
              if (item.brand case final value?)
                _DetailLine(label: 'Brand', value: value),
              if (item.barcode case final value?)
                _DetailLine(label: 'Barcode', value: value),
              if (item.description case final value?)
                _DetailLine(label: 'Description', value: value),
              if (item.unitPrice case final value?)
                _DetailLine(
                  label: 'Last printed rate',
                  value: formatInr(value, decimals: true),
                ),
              if (item.purchasePrice case final value?)
                _DetailLine(
                  label: 'Purchase price',
                  value: formatInr(value, decimals: true),
                ),
              if (item.sellingPrice case final value?)
                _DetailLine(
                  label: 'Selling price',
                  value: formatInr(value, decimals: true),
                ),
              if (item.mrp case final value?)
                _DetailLine(
                  label: 'MRP',
                  value: formatInr(value, decimals: true),
                ),
              if (item.gstRate case final value?)
                _DetailLine(label: 'GST', value: '$value%'),
              if (item.expiryDate case final value?)
                _DetailLine(label: 'Expiry date', value: value),
              if (item.batchNumber case final value?)
                _DetailLine(label: 'Batch number', value: value),
              _DetailLine(label: 'Store ID', value: item.storeId),
              const SizedBox(height: AppSpacing.xl),
              PrimaryButton(
                label: 'Record stock received',
                onPressed: () => _record(context, ref),
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                'History and forecast are unavailable because the backend does not expose those contracts yet.',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
        ),
        const SizedBox(width: 16),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
      ],
    ),
  );
}

class _StockAdjustmentSheet extends StatefulWidget {
  const _StockAdjustmentSheet({required this.item});

  final InventoryItem item;

  @override
  State<_StockAdjustmentSheet> createState() => _StockAdjustmentSheetState();
}

class _StockAdjustmentSheetState extends State<_StockAdjustmentSheet> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Record stock received',
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      const SizedBox(height: AppSpacing.xs),
      Text(
        'Enter the quantity received. Vyapar will apply it as a STOCK_RECEIVED inventory event.',
        style: Theme.of(
          context,
        ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
      ),
      const SizedBox(height: AppSpacing.lg),
      TextField(
        key: const ValueKey('stock_adjustment_field'),
        controller: _controller,
        autofocus: true,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: 'Change in ${widget.item.unit}'),
      ),
      const SizedBox(height: AppSpacing.lg),
      PrimaryButton(
        label: 'Save adjustment',
        onPressed: () {
          final value = double.tryParse(_controller.text.trim());
          if (value != null && value > 0) Navigator.of(context).pop(value);
        },
      ),
    ],
  );
}
