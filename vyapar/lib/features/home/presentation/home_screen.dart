import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';
import 'package:vyapar/features/recommendations/models/recommendation.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    await Future.wait([
      ref.read(merchantControllerProvider.notifier).refresh(),
      ref.read(inventoryControllerProvider.notifier).refresh(),
      ref.read(recommendationControllerProvider.notifier).refresh(),
      ref.read(analyticsControllerProvider.notifier).refresh(),
    ]);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => RefreshIndicator(
    onRefresh: () => _refresh(ref),
    child: CustomScrollView(
      key: const PageStorageKey('home_scroll'),
      physics: const AlwaysScrollableScrollPhysics(),
      slivers: const [
        SliverSection(child: SizedBox(height: 12)),
        SliverSection(child: _HomeHeader()),
        SliverSection(child: SizedBox(height: AppSpacing.lg)),
        SliverSection(child: _MunimHero()),
        SliverSection(child: SizedBox(height: AppSpacing.xl)),
        SliverSection(child: SectionHeader(title: 'Business pulse')),
        SliverSection(child: SizedBox(height: AppSpacing.sm)),
        _MetricGrid(),
        SliverSection(child: SizedBox(height: AppSpacing.xl)),
        SliverSection(child: _QuickActions()),
        SliverSection(child: SizedBox(height: AppSpacing.xl)),
        SliverSection(child: SectionHeader(title: 'Munim signals')),
        SliverSection(child: SizedBox(height: AppSpacing.xs)),
        _InsightList(),
        SliverPadding(padding: EdgeInsets.only(bottom: 110)),
      ],
    ),
  );
}

class _HomeHeader extends ConsumerWidget {
  const _HomeHeader();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(merchantControllerProvider);
    return AppHeader(
      title: profile.when(
        data: (value) => value.name,
        loading: () => 'Your business',
        error: (_, _) => 'Your business',
      ),
      subtitle: greetingFor(DateTime.now()),
      leading: const VyaparIcon(VyaparIcons.store, color: AppColors.navy),
      trailing: IconAction(
        icon: VyaparIcons.profile,
        label: 'Profile',
        onPressed: () => context.push('/more/profile'),
      ),
    );
  }
}

class _MunimHero extends ConsumerWidget {
  const _MunimHero();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inventory = ref.watch(inventoryControllerProvider);
    final lowCount = inventory.value?.where((item) => item.isLow).length;
    final message = switch ((inventory.isLoading, lowCount)) {
      (true, _) => 'Checking your shop now…',
      (_, null) => 'I couldn’t refresh your shop signals.',
      (_, 0) => 'No inventory item is below its reorder point.',
      (_, final count) =>
        '$count inventory ${count == 1 ? 'item needs' : 'items need'} attention.',
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.navyDeep, AppColors.navy, AppColors.blue],
        ),
        borderRadius: BorderRadius.circular(AppRadii.lg),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const AgentStatusIndicator(label: 'AI Munim', active: true),
            const SizedBox(height: AppSpacing.md),
            Text(
              message,
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(color: Colors.white),
            ),
            const SizedBox(height: AppSpacing.md),
            TextButton.icon(
              onPressed: () => context.go('/munim'),
              style: TextButton.styleFrom(foregroundColor: Colors.white),
              icon: const VyaparIcon(
                VyaparIcons.forward,
                color: Colors.white,
                size: 19,
              ),
              label: const Text('Open Munim'),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricGrid extends ConsumerWidget {
  const _MetricGrid();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analytics = ref.watch(analyticsControllerProvider);
    if (analytics.isLoading) {
      return const SliverSection(child: LoadingSkeleton(rows: 2));
    }
    if (analytics.hasError || analytics.value == null) {
      return SliverSection(
        child: AppErrorState(
          error: analytics.error ?? StateError('Analytics unavailable'),
          onRetry: ref.read(analyticsControllerProvider.notifier).refresh,
        ),
      );
    }
    final value = analytics.requireValue;
    final columns = MediaQuery.sizeOf(context).width >= 600 ? 3 : 2;
    return SliverPadding(
      padding: EdgeInsets.symmetric(
        horizontal: MediaQuery.sizeOf(context).width >= 600 ? 32 : 16,
      ),
      sliver: SliverGrid(
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: columns,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          mainAxisExtent: 124,
        ),
        delegate: SliverChildListDelegate.fixed([
          MetricTile(
            value: formatQuantity(value.salesQuantity),
            label: 'Units sold',
            accent: AppColors.blue,
          ),
          MetricTile(
            value: '${value.lowInventoryProducts}',
            label: 'Low-stock items',
            accent: value.lowInventoryProducts > 0
                ? AppColors.warning
                : AppColors.success,
          ),
          MetricTile(
            value: '${value.totalOrders}',
            label: 'Orders recorded',
            accent: AppColors.navy,
          ),
        ]),
      ),
    );
  }
}

class _QuickActions extends StatelessWidget {
  const _QuickActions();

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const SectionHeader(title: 'Quick actions'),
      const SizedBox(height: AppSpacing.sm),
      Wrap(
        spacing: AppSpacing.xs,
        runSpacing: AppSpacing.xs,
        children: [
          _QuickAction(
            label: 'Inventory',
            icon: VyaparIcons.inventory,
            onTap: () => context.go('/inventory'),
          ),
          _QuickAction(
            label: 'Recommendations',
            icon: VyaparIcons.insight,
            onTap: () => context.push('/recommendations'),
          ),
          _QuickAction(
            label: 'Analytics',
            icon: VyaparIcons.analytics,
            onTap: () => context.push('/analytics'),
          ),
          _QuickAction(
            label: 'Ask Munim',
            icon: VyaparIcons.mic,
            onTap: () => context.push('/voice'),
          ),
        ],
      ),
    ],
  );
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final List<List<dynamic>> icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
    avatar: VyaparIcon(icon, size: 19, color: AppColors.navy),
    label: Text(label),
    onPressed: onTap,
    backgroundColor: AppColors.surface,
    side: const BorderSide(color: AppColors.outline),
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
  );
}

class _InsightList extends ConsumerWidget {
  const _InsightList();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendations = ref.watch(recommendationControllerProvider);
    return recommendations.when(
      loading: () => const SliverSection(child: LoadingSkeleton(rows: 3)),
      error: (error, _) => SliverSection(
        child: AppErrorState(
          error: error,
          onRetry: ref.read(recommendationControllerProvider.notifier).refresh,
        ),
      ),
      data: (items) {
        if (items.isEmpty) {
          return const SliverSection(
            child: EmptyState(
              title: 'No new recommendations',
              message: 'Munim has no new recommendations right now.',
            ),
          );
        }
        final visible = items.take(4).toList(growable: false);
        return SliverPadding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          sliver: SliverList.separated(
            itemCount: visible.length,
            separatorBuilder: (context, index) => const Divider(indent: 48),
            itemBuilder: (context, index) =>
                _InsightRow(recommendation: visible[index]),
          ),
        );
      },
    );
  }
}

class _InsightRow extends StatelessWidget {
  const _InsightRow({required this.recommendation});

  final Recommendation recommendation;

  @override
  Widget build(BuildContext context) => ListTile(
    contentPadding: const EdgeInsets.symmetric(vertical: 6),
    leading: const VyaparIcon(VyaparIcons.insight, color: AppColors.blue),
    title: Text(recommendation.sku),
    subtitle: Text('Priority score ${recommendation.score.toStringAsFixed(2)}'),
    trailing: const VyaparIcon(VyaparIcons.forward, size: 18),
    onTap: () => context.push('/recommendations/${recommendation.sku}'),
  );
}
