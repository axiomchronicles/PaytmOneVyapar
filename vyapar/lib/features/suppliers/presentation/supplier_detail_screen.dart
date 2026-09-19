import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';
import 'package:vyapar/features/suppliers/models/supplier.dart';
import 'package:vyapar/features/suppliers/providers/supplier_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class SupplierDetailScreen extends ConsumerWidget {
  const SupplierDetailScreen({required this.supplierId, super.key});

  final String supplierId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final supplier = ref.watch(supplierDetailProvider(supplierId));
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Supplier detail',
                  subtitle: supplierId,
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                ),
              ),
            ),
            supplier.when(
              loading: () =>
                  const SliverToBoxAdapter(child: SupplierDetailSkeleton()),
              error: (error, _) => SliverFillRemaining(
                hasScrollBody: false,
                child: AppErrorState(error: error),
              ),
              data: (value) => SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                sliver: SliverList.list(
                  children: [
                    Text(
                      value.name,
                      style: Theme.of(context).textTheme.headlineLarge,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    StatusPill(
                      label: value.isActive ? 'Active' : 'Unavailable',
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      '${value.productCount} catalog products · ${(value.trustScore * 100).round()}% trust',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    if (value.category != null || value.city != null) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        [value.category, value.city, value.state]
                            .whereType<String>()
                            .where((part) => part.isNotEmpty)
                            .join(' · '),
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                    if (value.phoneNumber != null || value.gstin != null) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        [
                          if (value.phoneNumber case final phone?)
                            'Phone: $phone',
                          if (value.gstin case final gstin?) 'GSTIN: $gstin',
                        ].join(' · '),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                    const SizedBox(height: AppSpacing.xl),
                    const SectionHeader(title: 'Available products'),
                    for (final product in value.products)
                      SupplierProductRequestTile(
                        supplierId: value.id,
                        supplierName: value.name,
                        product: product,
                      ),
                    if (value.products.isEmpty)
                      const EmptyState(
                        title: 'No matching products',
                        message:
                            'This supplier has no products for your catalog.',
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

class SupplierProductRequestTile extends ConsumerWidget {
  const SupplierProductRequestTile({
    required this.supplierId,
    required this.supplierName,
    required this.product,
    super.key,
  });

  final String supplierId;
  final String supplierName;
  final SupplierProduct product;

  @override
  Widget build(BuildContext context, WidgetRef ref) => ListTile(
    contentPadding: EdgeInsets.zero,
    title: Text(product.productName),
    subtitle: Text(
      '${formatQuantity(product.availableQuantity)} ${product.unit} · ${product.leadTimeDays} day lead time',
    ),
    trailing: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(formatInr(product.unitPrice, decimals: true)),
        const SizedBox(height: AppSpacing.xxs),
        TextButton(
          key: Key('request_supplier_product_${product.id}'),
          onPressed: () async {
            final negotiationId = await showDialog<String>(
              context: context,
              builder: (_) => SupplierStockRequestDialog(
                supplierId: supplierId,
                supplierName: supplierName,
                product: product,
              ),
            );
            if (negotiationId != null && context.mounted) {
              await context.push('/negotiations/$negotiationId');
            }
          },
          child: const Text('Request stock'),
        ),
      ],
    ),
  );
}

class SupplierStockRequestDialog extends ConsumerStatefulWidget {
  const SupplierStockRequestDialog({
    required this.supplierId,
    required this.supplierName,
    required this.product,
    super.key,
  });

  final String supplierId;
  final String supplierName;
  final SupplierProduct product;

  @override
  ConsumerState<SupplierStockRequestDialog> createState() =>
      _SupplierStockRequestDialogState();
}

class _SupplierStockRequestDialogState
    extends ConsumerState<SupplierStockRequestDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _quantity;
  late final TextEditingController _targetPrice;
  late final TextEditingController _maxPrice;
  var _submitting = false;

  @override
  void initState() {
    super.initState();
    final listedPrice =
        double.tryParse(widget.product.unitPrice.toString()) ?? 1;
    _quantity = TextEditingController(text: '1');
    _targetPrice = TextEditingController(text: listedPrice.toStringAsFixed(2));
    _maxPrice = TextEditingController(
      text: (listedPrice * 1.2).toStringAsFixed(2),
    );
  }

  @override
  void dispose() {
    _quantity.dispose();
    _targetPrice.dispose();
    _maxPrice.dispose();
    super.dispose();
  }

  Future<void> _request() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final target = double.parse(_targetPrice.text.trim());
    final max = double.parse(_maxPrice.text.trim());
    if (target > max) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Maximum price must be at least the target price.'),
        ),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      final negotiation = await ref
          .read(negotiationListProvider.notifier)
          .startNegotiation(
            sku: widget.product.merchantSku,
            quantity: double.parse(_quantity.text.trim()),
            targetPrice: target,
            maxPrice: max,
            supplierId: widget.supplierId,
          );
      if (!mounted) return;
      Navigator.of(context).pop(negotiation.id);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not start this supplier request. Try again.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text('Request from ${widget.supplierName}'),
    content: Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(widget.product.productName),
          const SizedBox(height: AppSpacing.sm),
          SupplierRequestField(
            controller: _quantity,
            label: 'Quantity (${widget.product.unit})',
          ),
          SupplierRequestField(
            controller: _targetPrice,
            label: 'Target unit price (₹)',
          ),
          SupplierRequestField(
            controller: _maxPrice,
            label: 'Maximum unit price (₹)',
          ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: _submitting ? null : () => Navigator.of(context).pop(),
        child: const Text('Cancel'),
      ),
      FilledButton(
        key: Key('start_supplier_negotiation_${widget.product.id}'),
        onPressed: _submitting ? null : _request,
        child: _submitting
            ? const SizedBox.square(
                dimension: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Text('Start negotiation'),
      ),
    ],
  );
}

class SupplierRequestField extends StatelessWidget {
  const SupplierRequestField({
    required this.controller,
    required this.label,
    super.key,
  });

  final TextEditingController controller;
  final String label;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.xs),
    child: TextFormField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(labelText: label),
      validator: (value) {
        final number = double.tryParse(value?.trim() ?? '');
        return number == null || number <= 0
            ? 'Enter a value above zero'
            : null;
      },
    ),
  );
}
