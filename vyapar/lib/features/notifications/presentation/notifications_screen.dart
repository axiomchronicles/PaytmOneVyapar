import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/notifications/models/notification_item.dart';
import 'package:vyapar/features/notifications/providers/notification_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(notificationListProvider);
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: ref.read(notificationListProvider.notifier).refresh,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: 'Notifications',
                    subtitle: 'Updates from authoritative backend events',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                    trailing: IconAction(
                      icon: VyaparIcons.success,
                      label: 'Mark all read',
                      onPressed: ref
                          .read(notificationListProvider.notifier)
                          .markAllRead,
                    ),
                  ),
                ),
              ),
              notifications.when(
                loading: () =>
                    const SliverSection(child: ListSkeleton(rows: 7)),
                error: (error, _) => SliverFillRemaining(
                  hasScrollBody: false,
                  child: AppErrorState(error: error),
                ),
                data: (page) => page.items.isEmpty
                    ? const SliverFillRemaining(
                        hasScrollBody: false,
                        child: EmptyState(
                          title: 'You’re all caught up',
                          message:
                              'Approval, order, and inventory updates will appear here.',
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: page.items.length + (page.hasMore ? 1 : 0),
                          separatorBuilder: (_, _) => const Divider(indent: 48),
                          itemBuilder: (context, index) {
                            if (index == page.items.length) {
                              ref
                                  .read(notificationListProvider.notifier)
                                  .loadMore();
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            }
                            return _NotificationRow(item: page.items[index]);
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

class _NotificationRow extends ConsumerWidget {
  const _NotificationRow({required this.item});

  final NotificationItem item;

  void _open(BuildContext context, WidgetRef ref) {
    ref.read(notificationListProvider.notifier).markRead(item.id);
    final id = item.entityId;
    if (id == null) return;
    if (item.entityType == 'approval') context.push('/approval/$id');
    if (item.entityType == 'order') context.push('/order/$id');
    if (item.entityType == 'inventory') context.push('/inventory/$id');
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => ListTile(
    key: ValueKey('notification_${item.id}'),
    contentPadding: EdgeInsets.zero,
    minTileHeight: 78,
    leading: VyaparIcon(
      VyaparIcons.notification,
      color: item.isRead ? AppColors.muted : AppColors.blue,
    ),
    title: Text(
      item.title,
      style: TextStyle(
        fontWeight: item.isRead ? FontWeight.w400 : FontWeight.w700,
      ),
    ),
    subtitle: Text('${item.body}\n${formatDateTime(item.createdAt)}'),
    isThreeLine: true,
    onTap: () => _open(context, ref),
  );
}
