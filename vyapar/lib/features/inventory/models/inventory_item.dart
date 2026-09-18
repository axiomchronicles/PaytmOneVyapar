import 'package:vyapar/core/networking/json.dart';

class InventoryItem {
  const InventoryItem({
    required this.inventoryId,
    required this.storeId,
    required this.productId,
    required this.sku,
    required this.name,
    required this.unit,
    required this.quantityOnHand,
    required this.reorderPoint,
    required this.isLow,
  });

  factory InventoryItem.fromJson(JsonMap json) => InventoryItem(
    inventoryId: jsonString(json['inventory_id'], 'inventory_id'),
    storeId: jsonString(json['store_id'], 'store_id'),
    productId: jsonString(json['product_id'], 'product_id'),
    sku: jsonString(json['sku'], 'sku'),
    name: jsonString(json['name'], 'name'),
    unit: jsonString(json['unit'], 'unit'),
    quantityOnHand: jsonNumber(
      json['quantity_on_hand'],
      'quantity_on_hand',
    ).toDouble(),
    reorderPoint: jsonNumber(json['reorder_point'], 'reorder_point').toDouble(),
    isLow: jsonBool(json['is_low'], 'is_low'),
  );

  final String inventoryId;
  final String storeId;
  final String productId;
  final String sku;
  final String name;
  final String unit;
  final double quantityOnHand;
  final double reorderPoint;
  final bool isLow;
}
