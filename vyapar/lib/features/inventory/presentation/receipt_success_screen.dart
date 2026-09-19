import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/inventory/providers/receipt_scan_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class ReceiptSuccessScreen extends ConsumerWidget {
  const ReceiptSuccessScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(receiptScanControllerProvider);
    final result = state.confirmation;
    if (result == null) {
      return Scaffold(
        body: SafeArea(
          child: Center(
            child: AdaptivePadding(
              child: SecondaryButton(
                label: 'Back to inventory',
                onPressed: () => context.go('/inventory'),
              ),
            ),
          ),
        ),
      );
    }
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: AdaptivePadding(
          child: CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.xl),
                  child: Column(
                    children: [
                      VyaparIcon(
                        VyaparIcons.success,
                        size: 72,
                        color: AppColors.success,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Inventory updated',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        '${result.createdCount} new · ${result.updatedCount} existing · ${result.items.length} total',
                        style: Theme.of(
                          context,
                        ).textTheme.bodyLarge?.copyWith(color: AppColors.muted),
                      ),
                      const SizedBox(height: AppSpacing.xl),
                    ],
                  ),
                ),
              ),
              SliverList.builder(
                itemCount: result.items.length,
                itemBuilder: (context, index) {
                  final item = result.items[index];
                  return ListTile(
                    key: ValueKey('confirmed_${item.sku}'),
                    leading: VyaparIcon(
                      item.action == 'created'
                          ? VyaparIcons.add
                          : VyaparIcons.refresh,
                      color: AppColors.success,
                    ),
                    title: Text(item.name),
                    subtitle: Text('${item.sku} · ${item.action}'),
                    trailing: Text(
                      '+${formatQuantity(item.quantityAdded)} ${item.unit}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  );
                },
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.xxl)),
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: AdaptivePadding(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                PrimaryButton(
                  label: 'View inventory',
                  onPressed: () {
                    ref.read(receiptScanControllerProvider.notifier).reset();
                    context.go('/inventory');
                  },
                ),
                const SizedBox(height: AppSpacing.xs),
                AppButton(
                  label: state.manual
                      ? 'Add another product'
                      : 'Scan another receipt',
                  style: AppButtonStyle.text,
                  onPressed: () {
                    ref.read(receiptScanControllerProvider.notifier).reset();
                    context.go(
                      state.manual
                          ? '/inventory/add-product'
                          : '/inventory/scan-receipt',
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
