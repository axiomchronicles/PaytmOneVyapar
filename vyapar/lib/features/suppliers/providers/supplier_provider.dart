import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';
import 'package:vyapar/features/suppliers/data/supplier_repository.dart';
import 'package:vyapar/features/suppliers/models/supplier.dart';

final supplierRepositoryProvider = Provider<SupplierRepository>(
  (ref) => SupplierRepository(ref.watch(dioProvider)),
);

class SupplierListController extends AsyncNotifier<CursorPage<SupplierDetail>> {
  @override
  Future<CursorPage<SupplierDetail>> build() =>
      ref.watch(supplierRepositoryProvider).list();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(supplierRepositoryProvider).list(),
    );
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current?.nextCursor == null) return;
    final next = await ref
        .read(supplierRepositoryProvider)
        .list(cursor: current!.nextCursor);
    state = AsyncData(current.append(next, (item) => item.id));
  }
}

final supplierListProvider =
    AsyncNotifierProvider<SupplierListController, CursorPage<SupplierDetail>>(
      SupplierListController.new,
    );

final supplierDetailProvider = FutureProvider.autoDispose
    .family<SupplierDetail, String>(
      (ref, id) => ref.watch(supplierRepositoryProvider).get(id),
    );

final nearbySuppliersProvider =
    FutureProvider.autoDispose<List<NearbySupplier>>((ref) async {
  return ref.watch(supplierRepositoryProvider).discoverNearbySuppliers();
});

final nearbyMerchantsProvider =
    FutureProvider.autoDispose<List<NearbyMerchant>>((ref) async {
  return ref.watch(supplierRepositoryProvider).discoverNearbyMerchants();
});

final mySupplierProfileProvider =
    FutureProvider.autoDispose<SupplierDetail>((ref) async {
  return ref.watch(supplierRepositoryProvider).getMySupplierProfile();
});

final mySupplierOrdersProvider =
    FutureProvider.autoDispose<List<OrderDetail>>((ref) async {
  return ref.watch(supplierRepositoryProvider).getMySupplierOrders();
});
