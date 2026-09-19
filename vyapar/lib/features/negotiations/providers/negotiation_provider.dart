import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/features/negotiations/data/negotiation_repository.dart';
import 'package:vyapar/features/negotiations/models/negotiation.dart';

final negotiationRepositoryProvider = Provider<NegotiationRepository>(
  (ref) => NegotiationRepository(ref.watch(dioProvider)),
);

class NegotiationListController
    extends AsyncNotifier<CursorPage<NegotiationDetail>> {
  @override
  Future<CursorPage<NegotiationDetail>> build() =>
      ref.watch(negotiationRepositoryProvider).list();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(negotiationRepositoryProvider).list(),
    );
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current?.nextCursor == null) return;
    final next = await ref
        .read(negotiationRepositoryProvider)
        .list(cursor: current!.nextCursor);
    state = AsyncData(current.append(next, (item) => item.id));
  }

  Future<NegotiationDetail> startNegotiation({
    required String sku,
    String? storeId,
    num? quantity,
    num? targetPrice,
    num? maxPrice,
    String? supplierId,
  }) async {
    final item = await ref
        .read(negotiationRepositoryProvider)
        .start(
          sku: sku,
          storeId: storeId,
          quantity: quantity,
          targetPrice: targetPrice,
          maxPrice: maxPrice,
          supplierId: supplierId,
        );
    await refresh();
    return item;
  }
}

final negotiationListProvider =
    AsyncNotifierProvider<
      NegotiationListController,
      CursorPage<NegotiationDetail>
    >(NegotiationListController.new);

final negotiationDetailProvider = FutureProvider.autoDispose
    .family<NegotiationDetail, String>(
      (ref, id) => ref.watch(negotiationRepositoryProvider).get(id),
    );
