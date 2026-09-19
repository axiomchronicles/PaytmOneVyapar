import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/suppliers/models/supplier.dart';
import 'package:vyapar/features/suppliers/providers/supplier_provider.dart';

class SupplierInventoryScreen extends ConsumerWidget {
  const SupplierInventoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(mySupplierProfileProvider);
    return Scaffold(
      backgroundColor: AppColors.background,
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('add_supplier_catalog_item'),
        onPressed: () => context.push('/supplier-home/inventory/add'),
        backgroundColor: AppColors.navy,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Add item'),
      ),
      body: SafeArea(
        child: profile.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => AppErrorState(
            error: error,
            onRetry: () => ref.invalidate(mySupplierProfileProvider),
          ),
          data: (supplier) => CustomScrollView(
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: 'My inventory',
                    subtitle: 'Stock shown to merchants and Munim',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
              if (supplier.products.isEmpty)
                const SliverFillRemaining(
                  hasScrollBody: false,
                  child: EmptyState(
                    title: 'No catalog items yet',
                    message:
                        'Add stock to make it available for merchant orders.',
                  ),
                )
              else
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.md,
                    0,
                    AppSpacing.md,
                    96,
                  ),
                  sliver: SliverList.separated(
                    itemCount: supplier.products.length,
                    separatorBuilder: (_, _) =>
                        const SizedBox(height: AppSpacing.sm),
                    itemBuilder: (context, index) =>
                        SupplierCatalogTile(item: supplier.products[index]),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class SupplierCatalogTile extends StatelessWidget {
  const SupplierCatalogTile({required this.item, super.key});

  final SupplierProduct item;

  @override
  Widget build(BuildContext context) => Semantics(
    label:
        '${item.productName}, ${item.availableQuantity} ${item.unit} available',
    child: Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: AppColors.outline),
      ),
      child: Row(
        children: [
          const CircleAvatar(
            backgroundColor: AppColors.paleBlue,
            child: Icon(Icons.inventory_2_outlined, color: AppColors.navy),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.productName,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  '${item.merchantSku} · ${item.availableQuantity} ${item.unit} in stock',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                ),
              ],
            ),
          ),
          Text(
            '₹${item.unitPrice}',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: AppColors.success),
          ),
        ],
      ),
    ),
  );
}

class SupplierInventoryFormScreen extends ConsumerStatefulWidget {
  const SupplierInventoryFormScreen({super.key});

  @override
  ConsumerState<SupplierInventoryFormScreen> createState() =>
      _SupplierInventoryFormScreenState();
}

class _SupplierInventoryFormScreenState
    extends ConsumerState<SupplierInventoryFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _sku = TextEditingController();
  final _supplierSku = TextEditingController();
  final _unit = TextEditingController(text: 'pack');
  final _quantity = TextEditingController();
  final _price = TextEditingController();
  final _leadTime = TextEditingController(text: '1');
  final _category = TextEditingController();
  var _saving = false;

  @override
  void dispose() {
    _name.dispose();
    _sku.dispose();
    _supplierSku.dispose();
    _unit.dispose();
    _quantity.dispose();
    _price.dispose();
    _leadTime.dispose();
    _category.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _saving = true);
    try {
      await ref
          .read(supplierRepositoryProvider)
          .upsertMyProduct(
            sku: _sku.text.trim(),
            name: _name.text.trim(),
            unit: _unit.text.trim(),
            availableQuantity: double.parse(_quantity.text.trim()),
            unitPrice: double.parse(_price.text.trim()),
            leadTimeDays: int.parse(_leadTime.text.trim()),
            category: _category.text.trim(),
            supplierSku: _supplierSku.text.trim(),
          );
      ref.invalidate(mySupplierProfileProvider);
      ref.invalidate(nearbySuppliersProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Inventory item is now available to merchants.'),
        ),
      );
      context.pop();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not save the inventory item. Try again.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.background,
    body: SafeArea(
      child: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: [
            AppHeader(
              title: 'Add inventory item',
              subtitle:
                  'This stock can receive automated replenishment requests.',
              leading: IconAction(
                icon: VyaparIcons.back,
                label: 'Back',
                onPressed: context.pop,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            SupplierInventoryField(
              controller: _name,
              label: 'Product name',
              textCapitalization: TextCapitalization.words,
            ),
            SupplierInventoryField(
              controller: _sku,
              label: 'Merchant SKU',
              hint: 'Example: COLD-COLA-300',
              textCapitalization: TextCapitalization.characters,
            ),
            SupplierInventoryField(
              controller: _supplierSku,
              label: 'Your SKU (optional)',
              textCapitalization: TextCapitalization.characters,
              required: false,
            ),
            SupplierInventoryField(
              controller: _unit,
              label: 'Unit',
              hint: 'pack, crate, bag',
            ),
            SupplierInventoryField(
              controller: _quantity,
              label: 'Available quantity',
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
            ),
            SupplierInventoryField(
              controller: _price,
              label: 'Wholesale unit price (₹)',
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
            ),
            SupplierInventoryField(
              controller: _leadTime,
              label: 'Lead time (days)',
              keyboardType: TextInputType.number,
            ),
            SupplierInventoryField(
              controller: _category,
              label: 'Category (optional)',
              required: false,
            ),
            const SizedBox(height: AppSpacing.md),
            AppButton(
              key: const Key('save_supplier_catalog_item'),
              label: 'Publish inventory',
              loading: _saving,
              onPressed: _save,
            ),
            const SizedBox(height: AppSpacing.xl),
          ],
        ),
      ),
    ),
  );
}

class SupplierInventoryField extends StatelessWidget {
  const SupplierInventoryField({
    required this.controller,
    required this.label,
    super.key,
    this.hint,
    this.keyboardType,
    this.textCapitalization = TextCapitalization.none,
    this.required = true,
  });

  final TextEditingController controller;
  final String label;
  final String? hint;
  final TextInputType? keyboardType;
  final TextCapitalization textCapitalization;
  final bool required;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      textCapitalization: textCapitalization,
      decoration: InputDecoration(labelText: label, hintText: hint),
      validator: (value) {
        final input = value?.trim() ?? '';
        if (required && input.isEmpty) return '$label is required';
        if (input.isEmpty) return null;
        if (keyboardType == TextInputType.number ||
            keyboardType ==
                const TextInputType.numberWithOptions(decimal: true)) {
          if (double.tryParse(input) == null || double.parse(input) < 0) {
            return 'Enter a valid value';
          }
        }
        return null;
      },
    ),
  );
}
