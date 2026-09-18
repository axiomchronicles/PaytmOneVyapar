import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/suppliers/models/supplier.dart';
import 'package:vyapar/features/suppliers/providers/supplier_provider.dart';

class SuppliersScreen extends ConsumerWidget {
  const SuppliersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final suppliers = ref.watch(supplierListProvider);
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: ref.read(supplierListProvider.notifier).refresh,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: 'Suppliers',
                    subtitle: 'Catalog availability from connected suppliers',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
              suppliers.when(
                loading: () =>
                    const SliverSection(child: ListSkeleton(rows: 6)),
                error: (error, _) => SliverFillRemaining(
                  hasScrollBody: false,
                  child: AppErrorState(
                    error: error,
                    onRetry: ref.read(supplierListProvider.notifier).refresh,
                  ),
                ),
                data: (page) => page.items.isEmpty
                    ? const SliverFillRemaining(
                        hasScrollBody: false,
                        child: EmptyState(
                          title: 'No suppliers',
                          message:
                              'Connected supplier catalogs will appear here.',
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: page.items.length + (page.hasMore ? 1 : 0),
                          separatorBuilder: (_, _) => const Divider(indent: 52),
                          itemBuilder: (context, index) {
                            if (index == page.items.length) {
                              ref
                                  .read(supplierListProvider.notifier)
                                  .loadMore();
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            }
                            return _SupplierRow(supplier: page.items[index]);
                          },
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SupplierRow extends StatelessWidget {
  const _SupplierRow({required this.supplier});

  final SupplierDetail supplier;

  @override
  Widget build(BuildContext context) => ListTile(
    key: ValueKey('supplier_${supplier.id}'),
    minTileHeight: 72,
    contentPadding: EdgeInsets.zero,
    leading: const VyaparIcon(VyaparIcons.store, color: AppColors.blue),
    title: Text(supplier.name),
    subtitle: Text('${supplier.productCount} catalog products'),
    trailing: const VyaparIcon(VyaparIcons.forward, size: 18),
    onTap: () => context.push('/suppliers/${supplier.id}'),
  );
}
