import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';

class RecommendationsScreen extends ConsumerWidget {
  const RecommendationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendations = ref.watch(recommendationControllerProvider);
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: ref
              .read(recommendationControllerProvider.notifier)
              .refresh,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: 'Munim recommendations',
                    subtitle: 'Ranked signals from current inventory',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
              recommendations.when(
                loading: () => const SliverPadding(
                  padding: EdgeInsets.all(AppSpacing.md),
                  sliver: SliverToBoxAdapter(child: LoadingSkeleton(rows: 5)),
                ),
                error: (error, _) => SliverFillRemaining(
                  hasScrollBody: false,
                  child: AppErrorState(
                    error: error,
                    onRetry: ref
                        .read(recommendationControllerProvider.notifier)
                        .refresh,
                  ),
                ),
                data: (items) => items.isEmpty
                    ? const SliverFillRemaining(
                        hasScrollBody: false,
                        child: EmptyState(
                          title: 'No new recommendations',
                          message:
                              'Munim has no new recommendations right now.',
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: items.length,
                          separatorBuilder: (context, index) =>
                              const Divider(indent: 48),
                          itemBuilder: (context, index) {
                            final item = items[index];
                            return ListTile(
                              leading: const VyaparIcon(
                                VyaparIcons.insight,
                                color: AppColors.blue,
                              ),
                              title: Text(item.sku),
                              subtitle: Text(
                                'Priority score ${item.score.toStringAsFixed(2)}',
                              ),
                              trailing: const VyaparIcon(
                                VyaparIcons.forward,
                                size: 18,
                              ),
                              onTap: () =>
                                  context.push('/recommendations/${item.sku}'),
                            );
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
