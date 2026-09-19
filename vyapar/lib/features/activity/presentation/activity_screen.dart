import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
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
    final theme = Theme.of(context);

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
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.md,
                  0,
                  AppSpacing.md,
                  AppSpacing.md,
                ),
                child: Container(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  decoration: BoxDecoration(
                    color: AppColors.paleBlue,
                    borderRadius: BorderRadius.circular(AppRadii.sm),
                    border: Border.all(
                      color: AppColors.blue.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Row(
                    children: [
                      const VyaparIcon(
                        VyaparIcons.security,
                        size: 16,
                        color: AppColors.blue,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'vyapaar-a2a-v1 mutual cryptographic protocol with HMAC-SHA256 signatures.',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: AppColors.navy,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ],
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
              data: (items) => items.isEmpty
                  ? const SliverFillRemaining(
                      hasScrollBody: false,
                      child: EmptyState(
                        title: 'No conversation messages',
                        message:
                            'No cryptographic envelopes found for this correlation ID.',
                      ),
                    )
                  : SliverPadding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.md,
                      ),
                      sliver: SliverList.separated(
                        itemCount: items.length,
                        separatorBuilder: (_, _) =>
                            const SizedBox(height: AppSpacing.sm),
                        itemBuilder: (context, index) =>
                            _A2AMessageCard(item: items[index]),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _A2AMessageCard extends StatelessWidget {
  const _A2AMessageCard({required this.item});

  final ActivityItem item;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isOutbound = (item.subtitle ?? '').toUpperCase() == 'OUTBOUND';
    final payload = item.payload ?? const {};

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(
          color: isOutbound
              ? AppColors.blue.withValues(alpha: 0.3)
              : AppColors.success.withValues(alpha: 0.3),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: isOutbound
                        ? AppColors.paleBlue
                        : AppColors.successSurface,
                    borderRadius: BorderRadius.circular(AppRadii.pill),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      VyaparIcon(
                        isOutbound ? VyaparIcons.forward : VyaparIcons.back,
                        size: 12,
                        color: isOutbound ? AppColors.navy : AppColors.success,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        isOutbound
                            ? 'OUTBOUND → Supplier'
                            : 'INBOUND ← Supplier',
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: isOutbound
                              ? AppColors.navy
                              : AppColors.success,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.background,
                    borderRadius: BorderRadius.circular(AppRadii.pill),
                    border: Border.all(color: AppColors.outline),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const VyaparIcon(
                        VyaparIcons.security,
                        size: 10,
                        color: AppColors.success,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'HMAC Verified',
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: AppColors.muted,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                Expanded(
                  child: Text(
                    sentenceCase(item.title),
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                StatusPill(
                  label: item.kind,
                  tone: isOutbound ? StatusTone.info : StatusTone.success,
                ),
              ],
            ),
            if (payload.isNotEmpty) ...[
              const Divider(height: AppSpacing.md),
              Wrap(
                spacing: 12,
                runSpacing: 6,
                children: [
                  if (payload['sku'] != null)
                    _PayloadField(
                      label: 'SKU',
                      value: payload['sku'].toString(),
                    ),
                  if (payload['unit_price'] != null)
                    _PayloadField(
                      label: 'Price',
                      value: formatInr(
                        num.tryParse(payload['unit_price'].toString()) ?? 0,
                        decimals: true,
                      ),
                    ),
                  if (payload['quantity'] != null)
                    _PayloadField(
                      label: 'Quantity',
                      value: '${payload['quantity']} units',
                    ),
                  if (payload['delivery_days'] != null)
                    _PayloadField(
                      label: 'Delivery',
                      value: '${payload['delivery_days']} days',
                    ),
                  if (payload['notes'] != null)
                    _PayloadField(
                      label: 'Notes',
                      value: payload['notes'].toString(),
                    ),
                ],
              ),
            ],
            const Divider(height: AppSpacing.md),
            Row(
              children: [
                if (item.messageId != null)
                  Expanded(
                    child: Text(
                      'Msg: ${item.messageId}',
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: AppColors.muted,
                        fontSize: 10,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ),
                Text(
                  formatDateTime(item.occurredAt),
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: AppColors.muted,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _PayloadField extends StatelessWidget {
  const _PayloadField({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$label: ',
          style: theme.textTheme.labelSmall?.copyWith(color: AppColors.muted),
        ),
        Text(
          value,
          style: theme.textTheme.labelSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
