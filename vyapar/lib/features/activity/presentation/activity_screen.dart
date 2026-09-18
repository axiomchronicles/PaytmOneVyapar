import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/activity/models/activity.dart';
import 'package:vyapar/features/activity/providers/activity_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class ActivityScreen extends ConsumerWidget {
  const ActivityScreen({required this.a2a, super.key});

  final bool a2a;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(
      a2a ? a2aActivityProvider : businessActivityProvider,
    );
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () => a2a
              ? ref.read(a2aActivityProvider.notifier).refresh()
              : ref.read(businessActivityProvider.notifier).refresh(),
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: a2a ? 'A2A activity' : 'Business history',
                    subtitle: a2a
                        ? 'Human-readable supplier-agent exchanges'
                        : 'Authoritative business audit trail',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
              if (!a2a)
                SliverSection(
                  child: _HistoryFilters(
                    selected: ref.watch(historyFilterProvider).label,
                    onCustom: () async {
                      final now = DateTime.now();
                      final range = await showDateRangePicker(
                        context: context,
                        firstDate: DateTime(now.year - 2),
                        lastDate: now,
                      );
                      if (range != null) {
                        ref
                            .read(historyFilterProvider.notifier)
                            .custom(range.start, range.end);
                      }
                    },
                  ),
                ),
              state.when(
                loading: () =>
                    const SliverSection(child: ListSkeleton(rows: 7)),
                error: (error, _) => SliverFillRemaining(
                  hasScrollBody: false,
                  child: AppErrorState(error: error),
                ),
                data: (page) => _ActivitySliver(
                  page: page,
                  a2a: a2a,
                  onMore: () => a2a
                      ? ref.read(a2aActivityProvider.notifier).loadMore()
                      : ref.read(businessActivityProvider.notifier).loadMore(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HistoryFilters extends ConsumerWidget {
  const _HistoryFilters({required this.selected, required this.onCustom});

  final String selected;
  final VoidCallback onCustom;

  @override
  Widget build(BuildContext context, WidgetRef ref) => SingleChildScrollView(
    scrollDirection: Axis.horizontal,
    child: Row(
      children: [
        AppChip(
          label: 'Today',
          selected: selected == 'Today',
          onTap: ref.read(historyFilterProvider.notifier).today,
        ),
        const SizedBox(width: AppSpacing.xs),
        AppChip(
          label: 'Yesterday',
          selected: selected == 'Yesterday',
          onTap: ref.read(historyFilterProvider.notifier).yesterday,
        ),
        const SizedBox(width: AppSpacing.xs),
        AppChip(
          label: 'This week',
          selected: selected == 'This week',
          onTap: ref.read(historyFilterProvider.notifier).week,
        ),
        const SizedBox(width: AppSpacing.xs),
        AppChip(
          label: 'This month',
          selected: selected == 'This month',
          onTap: ref.read(historyFilterProvider.notifier).month,
        ),
        const SizedBox(width: AppSpacing.xs),
        AppChip(
          label: 'Custom',
          selected: selected == 'Custom',
          onTap: onCustom,
        ),
      ],
    ),
  );
}

class _ActivitySliver extends StatelessWidget {
  const _ActivitySliver({
    required this.page,
    required this.onMore,
    required this.a2a,
  });

  final CursorPage<ActivityItem> page;
  final VoidCallback onMore;
  final bool a2a;

  @override
  Widget build(BuildContext context) => page.items.isEmpty
      ? const SliverFillRemaining(
          hasScrollBody: false,
          child: EmptyState(
            title: 'No activity yet',
            message: 'Recorded business events will appear here.',
          ),
        )
      : SliverPadding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          sliver: SliverList.separated(
            itemCount: page.items.length + (page.hasMore ? 1 : 0),
            separatorBuilder: (_, _) => const Divider(indent: 44),
            itemBuilder: (context, index) {
              if (index == page.items.length) {
                onMore();
                return const Center(child: CircularProgressIndicator());
              }
              final item = page.items[index];
              return ListTile(
                key: ValueKey('activity_${item.id}'),
                contentPadding: EdgeInsets.zero,
                leading: const VyaparIcon(VyaparIcons.clock),
                title: Text(sentenceCase(item.title)),
                subtitle: Text(formatDateTime(item.occurredAt)),
                onTap: item.entityId == null
                    ? item.correlationId == null || !a2a
                          ? null
                          : () => context.push(
                              '/a2a-activity/${item.correlationId}',
                            )
                    : () {
                        if (item.entityType == 'order') {
                          context.push('/order/${item.entityId}');
                        } else if (item.entityType == 'approval') {
                          context.push('/approval/${item.entityId}');
                        } else if (item.entityType == 'negotiation') {
                          context.push('/negotiations/${item.entityId}');
                        }
                      },
              );
            },
          ),
        );
}

class A2AConversationScreen extends ConsumerWidget {
  const A2AConversationScreen({required this.correlationId, super.key});

  final String correlationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conversation = ref.watch(a2aConversationProvider(correlationId));
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'A2A conversation',
                  subtitle: correlationId,
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                ),
              ),
            ),
            conversation.when(
              loading: () =>
                  const SliverSection(child: A2AConversationSkeleton()),
              error: (error, _) => SliverFillRemaining(
                hasScrollBody: false,
                child: AppErrorState(error: error),
              ),
              data: (items) => SliverSection(
                child: AppTimeline(
                  items: [
                    for (final item in items)
                      TimelineItem(
                        title: item.title,
                        subtitle:
                            '${item.subtitle} · ${formatDateTime(item.occurredAt)}',
                        complete: true,
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
