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
    this.category,
    this.barcode,
    this.brand,
    this.description,
    this.unitPrice,
    this.purchasePrice,
    this.sellingPrice,
    this.mrp,
    this.gstRate,
    this.expiryDate,
    this.batchNumber,
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
    category: jsonOptionalString(json['category']),
    barcode: jsonOptionalString(json['barcode']),
    brand: jsonOptionalString(json['brand']),
    description: jsonOptionalString(json['description']),
    unitPrice: _optionalNumber(json['unit_price']),
    purchasePrice: _optionalNumber(json['purchase_price']),
    sellingPrice: _optionalNumber(json['selling_price']),
    mrp: _optionalNumber(json['mrp']),
    gstRate: _optionalNumber(json['gst_rate']),
    expiryDate: jsonOptionalString(json['expiry_date']),
    batchNumber: jsonOptionalString(json['batch_number']),
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
  final String? category;
  final String? barcode;
  final String? brand;
  final String? description;
  final double? unitPrice;
  final double? purchasePrice;
  final double? sellingPrice;
  final double? mrp;
  final double? gstRate;
  final String? expiryDate;
  final String? batchNumber;
}

double? _optionalNumber(Object? value) =>
    value == null ? null : jsonNumber(value, 'optional_number').toDouble();
