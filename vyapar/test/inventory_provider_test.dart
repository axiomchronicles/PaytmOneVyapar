import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/features/inventory/data/inventory_repository.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';

class _FakeInventoryRepository extends InventoryRepository {
  _FakeInventoryRepository(this.items) : super(Dio());

  final List<InventoryItem> items;

  @override
  Future<List<InventoryItem>> list({
    String? storeId,
    CancelToken? cancelToken,
  }) async => items
      .where((item) => storeId == null || item.storeId == storeId)
      .toList();
}

const _cola = InventoryItem(
  inventoryId: 'inventory-cola',
  storeId: 'store-one',
  productId: 'product-cola',
  sku: 'COLD-COLA-300',
  name: 'Cola crate',
  unit: 'crate',
  quantityOnHand: 3,
  reorderPoint: 8,
  isLow: true,
);

const _rice = InventoryItem(
  inventoryId: 'inventory-rice',
  storeId: 'store-two',
  productId: 'product-rice',
  sku: 'RICE-5KG',
  name: 'Rice bag',
  unit: 'bag',
  quantityOnHand: 12,
  reorderPoint: 5,
  isLow: false,
);

void main() {
  test('inventory provider loads repository data', () async {
    final container = ProviderContainer(
      overrides: [
        inventoryRepositoryProvider.overrideWithValue(
          _FakeInventoryRepository(const [_cola, _rice]),
        ),
      ],
    );
    addTearDown(container.dispose);

    final items = await container.read(inventoryControllerProvider.future);
    expect(items, hasLength(2));
    expect(items.first.isLow, isTrue);
  });

  test(
    'inventory search is debounced and filters loaded server data',
    () async {
      final container = ProviderContainer(
        overrides: [
          inventoryRepositoryProvider.overrideWithValue(
            _FakeInventoryRepository(const [_cola, _rice]),
          ),
        ],
      );
      addTearDown(container.dispose);
      await container.read(inventoryControllerProvider.future);

      container.read(inventorySearchProvider.notifier).update('rice');
      expect(container.read(filteredInventoryProvider), hasLength(2));
      await Future<void>.delayed(const Duration(milliseconds: 300));
      expect(container.read(filteredInventoryProvider), [_rice]);
    },
  );
}
