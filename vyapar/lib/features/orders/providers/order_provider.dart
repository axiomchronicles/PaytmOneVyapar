import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/features/orders/data/order_repository.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';

final orderRepositoryProvider = Provider<OrderRepository>(
  (ref) => OrderRepository(ref.watch(dioProvider)),
);

final orderDetailProvider = FutureProvider.autoDispose
    .family<OrderDetail, String>(
      (ref, orderId) => ref.watch(orderRepositoryProvider).get(orderId),
    );

class OrderListController extends AsyncNotifier<CursorPage<OrderDetail>> {
  @override
  Future<CursorPage<OrderDetail>> build() =>
      ref.watch(orderRepositoryProvider).list();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(orderRepositoryProvider).list(),
    );
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current?.nextCursor == null) return;
    final next = await ref
        .read(orderRepositoryProvider)
        .list(cursor: current!.nextCursor);
    state = AsyncData(current.append(next, (item) => item.id));
  }
}

final orderListProvider =
    AsyncNotifierProvider<OrderListController, CursorPage<OrderDetail>>(
      OrderListController.new,
    );
