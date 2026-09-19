import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/inventory/models/receipt_scan.dart';
import 'package:vyapar/features/inventory/providers/receipt_scan_provider.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';

const _requiredItemFields = {'name', 'sku', 'quantity', 'unit'};

const _itemFields = <ReceiptFieldSpec>[
  ReceiptFieldSpec('name', 'Product name', required: true),
  ReceiptFieldSpec('sku', 'SKU', required: true),
  ReceiptFieldSpec('quantity', 'Quantity to add', required: true, numeric: true),
  ReceiptFieldSpec('unit', 'Unit', required: true, hint: 'piece, kg, box…'),
  ReceiptFieldSpec('barcode', 'Barcode', hint: 'Optional'),
  ReceiptFieldSpec('category', 'Category', hint: 'Optional'),
  ReceiptFieldSpec('brand', 'Brand', hint: 'Optional'),
  ReceiptFieldSpec(
    'description',
    'Description',
    hint: 'Optional',
    multiline: true,
  ),
  ReceiptFieldSpec(
    'unit_price',
    'Printed rate',
    numeric: true,
    hint: 'Optional',
  ),
  ReceiptFieldSpec(
    'purchase_price',
    'Purchase price',
    numeric: true,
    hint: 'Optional',
  ),
  ReceiptFieldSpec(
    'selling_price',
    'Selling price',
    numeric: true,
    hint: 'Optional',
  ),
  ReceiptFieldSpec('mrp', 'MRP', numeric: true, hint: 'Optional'),
  ReceiptFieldSpec('gst_rate', 'GST %', numeric: true, hint: 'Optional'),
  ReceiptFieldSpec('tax_amount', 'Tax amount', numeric: true, hint: 'Optional'),
  ReceiptFieldSpec('discount', 'Discount', numeric: true, hint: 'Optional'),
  ReceiptFieldSpec(
    'total_amount',
    'Line total',
    numeric: true,
    hint: 'Optional',
  ),
  ReceiptFieldSpec('expiry_date', 'Expiry date', hint: 'YYYY-MM-DD · Optional'),
  ReceiptFieldSpec('batch_number', 'Batch number', hint: 'Optional'),
];

const _receiptFields = <ReceiptFieldSpec>[
  ReceiptFieldSpec('supplier_name', 'Supplier name', hint: 'Optional'),
  ReceiptFieldSpec('invoice_number', 'Invoice number', hint: 'Optional'),
  ReceiptFieldSpec(
    'invoice_date',
    'Invoice date',
    hint: 'YYYY-MM-DD · Optional',
  ),
  ReceiptFieldSpec('currency', 'Currency', hint: 'Optional'),
  ReceiptFieldSpec('subtotal', 'Subtotal', numeric: true, hint: 'Optional'),
  ReceiptFieldSpec('tax', 'Receipt tax', numeric: true, hint: 'Optional'),
  ReceiptFieldSpec('total', 'Receipt total', numeric: true, hint: 'Optional'),
];

class ReceiptReviewScreen extends ConsumerWidget {
  const ReceiptReviewScreen({super.key});

  Future<void> _confirm(
    BuildContext context,
    WidgetRef ref,
    String? storeId,
  ) async {
    final success = await ref
        .read(receiptScanControllerProvider.notifier)
        .confirm(storeId);
    if (!context.mounted) return;
    if (success) {
      context.go('/inventory/scan-receipt/success');
      return;
    }
    final message = ref.read(receiptScanControllerProvider).failure?.message;
    if (message != null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(receiptScanControllerProvider);
    final review = state.review;
    final profile = ref.watch(merchantControllerProvider).value;
    final selected = ref.watch(selectedStoreProvider);
    final fallbackStore = profile == null || profile.stores.isEmpty
        ? null
        : profile.stores.first.id;
    final storeId = selected ?? fallbackStore;

    if (review == null) {
      return const ReceiptReviewUnavailable();
    }
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: CustomScrollView(
          key: const PageStorageKey('receipt_review_scroll'),
          slivers: [
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.md),
                  child: AppHeader(
                    title: state.manual ? 'Add inventory' : 'Review & correct',
                    subtitle: state.manual
                        ? 'Enter product, quantity, prices, taxes, and other details'
                        : '${review.items.length} products detected',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.md),
                  child: ReceiptReviewLegend(
                    warningCount: review.items.fold(
                      0,
                      (total, item) => total + item.lowConfidenceFields.length,
                    ),
                    missingRequiredCount: review.items.fold(
                      0,
                      (total, item) =>
                          total +
                          _requiredItemFields
                              .where(
                                (field) =>
                                    item.status(field) ==
                                    ReceiptFieldStatus.missing,
                              )
                              .length,
                    ),
                  ),
                ),
              ),
            ),
            if (state.failure case final failure?)
              SliverToBoxAdapter(
                child: AdaptivePadding(
                  child: Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.md),
                    child: ReceiptReviewError(message: failure.message),
                  ),
                ),
              ),
            if (!state.manual && review.warnings.isNotEmpty)
              SliverToBoxAdapter(
                child: AdaptivePadding(
                  child: Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.md),
                    child: ReceiptWarnings(warnings: review.warnings),
                  ),
                ),
              ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.md),
                  child: ReceiptStoreSelector(
                    stores: profile?.stores ?? const [],
                    selectedStoreId: storeId,
                    onChanged: ref.read(selectedStoreProvider.notifier).select,
                  ),
                ),
              ),
            ),
            if (!state.manual)
              SliverToBoxAdapter(
                child: AdaptivePadding(
                  child: Padding(
                    padding: const EdgeInsets.only(top: AppSpacing.md),
                    child: ReceiptHeaderEditor(
                      receipt: review.receipt,
                      onChanged: ref
                          .read(receiptScanControllerProvider.notifier)
                          .updateReceipt,
                    ),
                  ),
                ),
              ),
            SliverPadding(
              padding: const EdgeInsets.only(top: AppSpacing.md),
              sliver: SliverList.builder(
                itemCount: review.items.length,
                itemBuilder: (context, index) => AdaptivePadding(
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.md),
                    child: ReceiptItemEditor(
                      index: index,
                      item: review.items[index],
                      onChanged: (field, value) => ref
                          .read(receiptScanControllerProvider.notifier)
                          .updateItem(review.items[index].lineId, field, value),
                      onDelete: () => ref
                          .read(receiptScanControllerProvider.notifier)
                          .removeItem(review.items[index].lineId),
                    ),
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: SecondaryButton(
                  key: const ValueKey('add_receipt_item'),
                  label: 'Add product manually',
                  leading: VyaparIcon(VyaparIcons.add, color: AppColors.navy),
                  onPressed: ref
                      .read(receiptScanControllerProvider.notifier)
                      .addItem,
                ),
              ),
            ),
            const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.xxl)),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: AdaptivePadding(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: PrimaryButton(
              key: const ValueKey('confirm_receipt_inventory'),
              label: state.manual ? 'Save inventory' : 'Confirm inventory',
              loading: state.confirming,
              onPressed: () => _confirm(context, ref, storeId),
            ),
          ),
        ),
      ),
    );
  }
}

class ReceiptReviewUnavailable extends StatelessWidget {
  const ReceiptReviewUnavailable({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: AdaptivePadding(
          child: SecondaryButton(
            label: 'Scan a receipt',
            onPressed: () => context.go('/inventory/scan-receipt'),
          ),
        ),
      ),
    ),
  );
}

class ReceiptReviewLegend extends StatelessWidget {
  const ReceiptReviewLegend({
    required this.warningCount,
    required this.missingRequiredCount,
    super.key,
  });

  final int warningCount;
  final int missingRequiredCount;

  @override
  Widget build(BuildContext context) => Wrap(
    spacing: AppSpacing.xs,
    runSpacing: AppSpacing.xs,
    children: [
      const StatusPill(label: 'Blue: scanned', tone: StatusTone.info),
      if (warningCount > 0)
        StatusPill(label: '$warningCount uncertain', tone: StatusTone.warning),
      if (missingRequiredCount > 0)
        StatusPill(
          label: '$missingRequiredCount required missing',
          tone: StatusTone.danger,
        ),
      const StatusPill(label: 'Green: edited', tone: StatusTone.success),
    ],
  );
}

class ReceiptReviewError extends StatelessWidget {
  const ReceiptReviewError({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: AppColors.dangerSurface,
      borderRadius: BorderRadius.circular(AppRadii.sm),
    ),
    child: Padding(
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: Text(
        message,
        style: Theme.of(
          context,
        ).textTheme.bodyMedium?.copyWith(color: AppColors.danger),
      ),
    ),
  );
}

class ReceiptWarnings extends StatelessWidget {
  const ReceiptWarnings({required this.warnings, super.key});

  final List<String> warnings;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: AppColors.warningSurface,
      borderRadius: BorderRadius.circular(AppRadii.sm),
    ),
    child: Padding(
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Check these details',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: AppSpacing.xxs),
          for (final warning in warnings) Text('• $warning'),
        ],
      ),
    ),
  );
}

class ReceiptStoreSelector extends StatelessWidget {
  const ReceiptStoreSelector({
    required this.stores,
    required this.selectedStoreId,
    required this.onChanged,
    super.key,
  });

  final List<StoreSummary> stores;
  final String? selectedStoreId;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) => DropdownButtonFormField<String>(
    key: const ValueKey('receipt_store'),
    initialValue: selectedStoreId,
    decoration: const InputDecoration(labelText: 'Add stock to store'),
    items: [
      for (final store in stores)
        DropdownMenuItem(value: store.id, child: Text(store.name)),
    ],
    onChanged: stores.isEmpty ? null : onChanged,
  );
}

class ReceiptHeaderEditor extends StatelessWidget {
  const ReceiptHeaderEditor({
    required this.receipt,
    required this.onChanged,
    super.key,
  });

  final ReceiptMetadata receipt;
  final void Function(String field, String value) onChanged;

  @override
  Widget build(BuildContext context) => Material(
    color: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadii.md),
      side: const BorderSide(color: AppColors.outline),
    ),
    clipBehavior: Clip.antiAlias,
    child: ExpansionTile(
      title: const Text('Receipt details'),
      subtitle: const Text('Supplier, invoice, date, and totals'),
      childrenPadding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        0,
        AppSpacing.md,
        AppSpacing.md,
      ),
      children: [
        ResponsiveFieldGrid(
          children: [
            for (final spec in _receiptFields)
              ReceiptReviewField(
                fieldKey: ValueKey('receipt_${spec.name}'),
                spec: spec,
                value: receipt.value(spec.name),
                status: receipt.status(spec.name),
                confidence: receipt.fieldConfidence[spec.name],
                onChanged: (value) => onChanged(spec.name, value),
              ),
          ],
        ),
      ],
    ),
  );
}

class ReceiptItemEditor extends StatelessWidget {
  const ReceiptItemEditor({
    required this.index,
    required this.item,
    required this.onChanged,
    required this.onDelete,
    super.key,
  });

  final int index;
  final ReceiptReviewItem item;
  final void Function(String field, String value) onChanged;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final missingRequired = _requiredItemFields
        .where((field) => item.status(field) == ReceiptFieldStatus.missing)
        .length;
    return Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadii.md),
        side: BorderSide(
          color: missingRequired > 0 ? AppColors.danger : AppColors.outline,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        key: PageStorageKey('receipt_item_${item.lineId}'),
        initiallyExpanded: index == 0 || missingRequired > 0,
        leading: CircleAvatar(
          backgroundColor: AppColors.paleBlue,
          foregroundColor: AppColors.navy,
          child: Text('${index + 1}'),
        ),
        title: Text(item.value('name') ?? 'Unnamed product'),
        subtitle: Text(
          item.matchedProductId != null
              ? 'Existing product · stock will increase'
              : missingRequired > 0
              ? '$missingRequired required fields missing'
              : '${(item.confidence * 100).round()}% line confidence',
        ),
        trailing: IconButton(
          key: ValueKey('delete_${item.lineId}'),
          tooltip: 'Delete detected item',
          onPressed: onDelete,
          icon: VyaparIcon(VyaparIcons.delete, color: AppColors.danger),
        ),
        childrenPadding: const EdgeInsets.fromLTRB(
          AppSpacing.md,
          0,
          AppSpacing.md,
          AppSpacing.md,
        ),
        children: [
          if (item.sourceText case final source?) ...[
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Receipt: “$source”',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.muted),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
          ResponsiveFieldGrid(
            children: [
              for (final spec in _itemFields)
                ReceiptReviewField(
                  fieldKey: ValueKey('${item.lineId}_${spec.name}'),
                  spec: spec,
                  value: item.value(spec.name),
                  status: item.status(spec.name),
                  confidence: item.fieldConfidence[spec.name],
                  onChanged: (value) => onChanged(spec.name, value),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class ResponsiveFieldGrid extends StatelessWidget {
  const ResponsiveFieldGrid({required this.children, super.key});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final columns = constraints.maxWidth >= 680 ? 2 : 1;
      final width = columns == 2
          ? (constraints.maxWidth - AppSpacing.md) / 2
          : constraints.maxWidth;
      return Wrap(
        spacing: AppSpacing.md,
        runSpacing: AppSpacing.sm,
        children: [
          for (final child in children) SizedBox(width: width, child: child),
        ],
      );
    },
  );
}

class ReceiptReviewField extends StatelessWidget {
  const ReceiptReviewField({
    required this.spec,
    required this.status,
    required this.onChanged,
    super.key,
    this.value,
    this.confidence,
    this.fieldKey,
  });

  final ReceiptFieldSpec spec;
  final String? value;
  final ReceiptFieldStatus status;
  final double? confidence;
  final Key? fieldKey;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final (fill, helper, helperColor) = switch (status) {
      ReceiptFieldStatus.scanned => (
        AppColors.paleBlue,
        'From receipt · ${((confidence ?? 0) * 100).round()}%',
        AppColors.blue,
      ),
      ReceiptFieldStatus.uncertain => (
        AppColors.warningSurface,
        'Please check · ${((confidence ?? 0) * 100).round()}%',
        AppColors.warning,
      ),
      ReceiptFieldStatus.missing => (
        spec.required ? AppColors.dangerSurface : AppColors.background,
        spec.required ? 'Required · not found' : 'Not found · optional',
        spec.required ? AppColors.danger : AppColors.muted,
      ),
      ReceiptFieldStatus.edited => (
        AppColors.successSurface,
        'Edited by you',
        AppColors.success,
      ),
    };
    return TextFormField(
      key: fieldKey,
      initialValue: value,
      onChanged: onChanged,
      keyboardType: spec.numeric
          ? const TextInputType.numberWithOptions(decimal: true)
          : TextInputType.text,
      minLines: spec.multiline ? 2 : 1,
      maxLines: spec.multiline ? 3 : 1,
      decoration: InputDecoration(
        labelText: spec.label,
        hintText: spec.hint,
        filled: true,
        fillColor: fill,
        helperText: helper,
        helperStyle: TextStyle(color: helperColor),
      ),
    );
  }
}

class ReceiptFieldSpec {
  const ReceiptFieldSpec(
    this.name,
    this.label, {
    this.required = false,
    this.numeric = false,
    this.multiline = false,
    this.hint,
  });

  final String name;
  final String label;
  final bool required;
  final bool numeric;
  final bool multiline;
  final String? hint;
}
