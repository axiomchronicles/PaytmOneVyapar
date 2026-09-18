import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
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
              loading: () => const SliverToBoxAdapter(
                child: SupplierDetailSkeleton(),
              ),
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
                    const SizedBox(height: AppSpacing.xl),
                    const SectionHeader(title: 'Available products'),
                    for (final product in value.products)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(product.productName),
                        subtitle: Text(
                          '${formatQuantity(product.availableQuantity)} ${product.unit} · ${product.leadTimeDays} day lead time',
                        ),
                        trailing: Text(
                          formatInr(product.unitPrice, decimals: true),
                        ),
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
