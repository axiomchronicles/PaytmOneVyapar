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
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(merchantControllerProvider);
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Business profile',
                  subtitle: 'Merchant data from Vyapar',
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
                child: profile.when(
                  loading: () => const LoadingSkeleton(rows: 5),
                  error: (error, _) => AppErrorState(
                    error: error,
                    onRetry: ref
                        .read(merchantControllerProvider.notifier)
                        .refresh,
                  ),
                  data: (value) => _ProfileBody(profile: value),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileBody extends ConsumerWidget {
  const _ProfileBody({required this.profile});

  final MerchantProfile profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedStore = ref.watch(selectedStoreProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: AppSpacing.lg),
        Text(profile.name, style: Theme.of(context).textTheme.headlineLarge),
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Spending limit ${formatInr(profile.spendingLimit)} · ${profile.currency}',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(color: AppColors.muted),
        ),
        const SizedBox(height: AppSpacing.xl),
        const SectionHeader(title: 'Stores'),
        const SizedBox(height: AppSpacing.xs),
        if (profile.stores.isEmpty)
          const EmptyState(
            title: 'No stores found',
            message: 'Stores will appear when they are created in the backend.',
          )
        else
          for (final store in profile.stores)
            ListTile(
              minTileHeight: 64,
              contentPadding: EdgeInsets.zero,
              leading: const VyaparIcon(
                VyaparIcons.store,
                color: AppColors.blue,
              ),
              title: Text(store.name),
              subtitle: Text(store.id),
              trailing: selectedStore == store.id
                  ? const StatusPill(
                      label: 'Selected',
                      tone: StatusTone.success,
                    )
                  : null,
              onTap: () {
                ref.read(selectedStoreProvider.notifier).select(store.id);
                ref.invalidate(inventoryControllerProvider);
                ref.invalidate(recommendationControllerProvider);
              },
            ),
        if (selectedStore != null)
          TextButton(
            onPressed: () {
              ref.read(selectedStoreProvider.notifier).select(null);
              ref.invalidate(inventoryControllerProvider);
              ref.invalidate(recommendationControllerProvider);
            },
            child: const Text('Show all stores'),
          ),
      ],
    );
  }
}
