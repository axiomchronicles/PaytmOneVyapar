import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class NegotiationsScreen extends ConsumerWidget {
  const NegotiationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final negotiations = ref.watch(negotiationListProvider);
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: ref.read(negotiationListProvider.notifier).refresh,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: 'Negotiations',
                    subtitle: 'Supplier quotes and constrained counter offers',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
              negotiations.when(
                loading: () =>
                    const SliverSection(child: ListSkeleton(rows: 6)),
                error: (error, _) => SliverFillRemaining(
                  hasScrollBody: false,
                  child: AppErrorState(error: error),
                ),
                data: (page) => page.items.isEmpty
                    ? const SliverFillRemaining(
                        hasScrollBody: false,
                        child: EmptyState(
                          title: 'No negotiations yet',
                          message:
                              'Supplier conversations will appear after procurement starts.',
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: page.items.length + (page.hasMore ? 1 : 0),
                          separatorBuilder: (_, _) => const Divider(),
                          itemBuilder: (context, index) {
                            if (index == page.items.length) {
                              ref
                                  .read(negotiationListProvider.notifier)
                                  .loadMore();
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            }
                            final item = page.items[index];
                            return ListTile(
                              key: ValueKey('negotiation_${item.id}'),
                              contentPadding: EdgeInsets.zero,
                              title: Text('${item.supplierName} · ${item.sku}'),
                              subtitle: Text(
                                '${item.roundCount} events · ${formatDateTime(item.createdAt)}',
                              ),
                              trailing: StatusPill(
                                label: sentenceCase(item.status),
                              ),
                              onTap: () =>
                                  context.push('/negotiations/${item.id}'),
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
