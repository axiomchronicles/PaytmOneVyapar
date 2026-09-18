import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/inventory/data/inventory_repository.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';

final inventoryRepositoryProvider = Provider<InventoryRepository>(
  (ref) => InventoryRepository(ref.watch(dioProvider)),
);

class InventoryController extends AsyncNotifier<List<InventoryItem>> {
  CancelToken? _cancelToken;

  @override
  Future<List<InventoryItem>> build() async {
    final storeId = ref.watch(selectedStoreProvider);
    _cancelToken?.cancel();
    final token = CancelToken();
    _cancelToken = token;
    ref.onDispose(token.cancel);
    return ref
        .watch(inventoryRepositoryProvider)
        .list(storeId: storeId, cancelToken: token);
  }

  Future<void> refresh() async {
    _cancelToken?.cancel();
    final token = CancelToken();
    _cancelToken = token;
    state = await AsyncValue.guard(
      () => ref
          .read(inventoryRepositoryProvider)
          .list(storeId: ref.read(selectedStoreProvider), cancelToken: token),
    );
  }

  Future<void> recordAdjustment({
    required InventoryItem item,
    required double quantityDelta,
    required String eventType,
    required String idempotencyKey,
  }) async {
    await ref
        .read(inventoryRepositoryProvider)
        .recordEvent(
          item: item,
          quantityDelta: quantityDelta,
          eventType: eventType,
          idempotencyKey: idempotencyKey,
        );
    await refresh();
  }
}

final inventoryControllerProvider =
    AsyncNotifierProvider<InventoryController, List<InventoryItem>>(
      InventoryController.new,
    );

class InventorySearch extends Notifier<String> {
  Timer? _timer;

  @override
  String build() {
    ref.onDispose(() => _timer?.cancel());
    return '';
  }

  void update(String query) {
    _timer?.cancel();
    _timer = Timer(const Duration(milliseconds: 280), () {
      state = query.trim().toLowerCase();
    });
  }
}

final inventorySearchProvider = NotifierProvider<InventorySearch, String>(
  InventorySearch.new,
);

final filteredInventoryProvider = Provider<List<InventoryItem>>((ref) {
  final query = ref.watch(inventorySearchProvider);
  final inventory = ref.watch(inventoryControllerProvider).value ?? const [];
  if (query.isEmpty) return inventory;
  return inventory
      .where(
        (item) =>
            item.name.toLowerCase().contains(query) ||
            item.sku.toLowerCase().contains(query),
      )
      .toList(growable: false);
});

final inventoryDetailProvider = Provider.autoDispose
    .family<InventoryItem?, String>((ref, inventoryId) {
      final items = ref.watch(inventoryControllerProvider).value ?? const [];
      for (final item in items) {
        if (item.inventoryId == inventoryId) return item;
      }
      return null;
    });
