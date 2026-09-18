import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/features/notifications/data/notification_repository.dart';
import 'package:vyapar/features/notifications/models/notification_item.dart';

final notificationRepositoryProvider = Provider<NotificationRepository>(
  (ref) => NotificationRepository(ref.watch(dioProvider)),
);

class NotificationListController
    extends AsyncNotifier<CursorPage<NotificationItem>> {
  @override
  Future<CursorPage<NotificationItem>> build() =>
      ref.watch(notificationRepositoryProvider).list();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(notificationRepositoryProvider).list(),
    );
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current?.nextCursor == null) return;
    final next = await ref
        .read(notificationRepositoryProvider)
        .list(cursor: current!.nextCursor);
    state = AsyncData(current.append(next, (item) => item.id));
  }

  Future<void> markRead(String id) async {
    final current = state.value;
    if (current == null) return;
    final updated = await ref.read(notificationRepositoryProvider).markRead(id);
    state = AsyncData(
      CursorPage(
        items: [
          for (final item in current.items)
            if (item.id == id) updated else item,
        ],
        nextCursor: current.nextCursor,
      ),
    );
  }

  Future<void> markAllRead() async {
    await ref.read(notificationRepositoryProvider).markAllRead();
    await refresh();
  }
}

final notificationListProvider =
    AsyncNotifierProvider<
      NotificationListController,
      CursorPage<NotificationItem>
    >(NotificationListController.new);

final unreadNotificationCountProvider = Provider<int>((ref) {
  final page = ref.watch(notificationListProvider).value;
  return page?.items.where((item) => !item.isRead).length ?? 0;
});
