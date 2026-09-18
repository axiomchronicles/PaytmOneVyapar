import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/features/activity/data/activity_repository.dart';
import 'package:vyapar/features/activity/models/activity.dart';

final activityRepositoryProvider = Provider<ActivityRepository>(
  (ref) => ActivityRepository(ref.watch(dioProvider)),
);

class HistoryFilter {
  const HistoryFilter({
    required this.label,
    required this.from,
    required this.to,
  });

  final String label;
  final DateTime from;
  final DateTime to;
}

class HistoryFilterController extends Notifier<HistoryFilter> {
  @override
  HistoryFilter build() => _days('This week', 7);

  HistoryFilter _days(String label, int days) {
    final now = DateTime.now();
    return HistoryFilter(
      label: label,
      from: now.subtract(Duration(days: days)),
      to: now,
    );
  }

  void today() => state = _days('Today', 1);
  void yesterday() {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    state = HistoryFilter(
      label: 'Yesterday',
      from: today.subtract(const Duration(days: 1)),
      to: today,
    );
  }

  void week() => state = _days('This week', 7);
  void month() => state = _days('This month', 30);
  void custom(DateTime from, DateTime to) => state = HistoryFilter(
    label: 'Custom',
    from: from,
    to: to.add(const Duration(days: 1)),
  );
}

final historyFilterProvider =
    NotifierProvider<HistoryFilterController, HistoryFilter>(
      HistoryFilterController.new,
    );

abstract class _ActivityController
    extends AsyncNotifier<CursorPage<ActivityItem>> {
  Future<CursorPage<ActivityItem>> fetch({String? cursor});

  @override
  Future<CursorPage<ActivityItem>> build() => fetch();

  Future<void> refresh() async => state = await AsyncValue.guard(fetch);

  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current?.nextCursor == null) return;
    final next = await fetch(cursor: current!.nextCursor);
    state = AsyncData(current.append(next, (item) => item.id));
  }
}

class A2AActivityController extends _ActivityController {
  @override
  Future<CursorPage<ActivityItem>> fetch({String? cursor}) =>
      ref.read(activityRepositoryProvider).a2a(cursor: cursor);
}

class BusinessActivityController extends _ActivityController {
  @override
  Future<CursorPage<ActivityItem>> fetch({String? cursor}) {
    final filter = ref.watch(historyFilterProvider);
    return ref
        .read(activityRepositoryProvider)
        .business(cursor: cursor, from: filter.from, to: filter.to);
  }
}

final a2aActivityProvider =
    AsyncNotifierProvider<A2AActivityController, CursorPage<ActivityItem>>(
      A2AActivityController.new,
    );

final businessActivityProvider =
    AsyncNotifierProvider<BusinessActivityController, CursorPage<ActivityItem>>(
      BusinessActivityController.new,
    );

final a2aConversationProvider = FutureProvider.autoDispose
    .family<List<ActivityItem>, String>(
      (ref, id) => ref.watch(activityRepositoryProvider).conversation(id),
    );
