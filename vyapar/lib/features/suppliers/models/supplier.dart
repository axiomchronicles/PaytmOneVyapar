import 'package:decimal/decimal.dart';
import 'package:vyapar/core/networking/json.dart';

class SupplierProduct {
  const SupplierProduct({
    required this.id,
    required this.productId,
    required this.supplierSku,
    required this.productName,
    required this.merchantSku,
    required this.unit,
    required this.availableQuantity,
    required this.unitPrice,
    required this.leadTimeDays,
  });

  factory SupplierProduct.fromJson(JsonMap json) => SupplierProduct(
    id: jsonString(json['id'], 'id'),
    productId: jsonString(json['product_id'], 'product_id'),
    supplierSku: jsonString(json['supplier_sku'], 'supplier_sku'),
    productName: jsonString(json['product_name'], 'product_name'),
    merchantSku: jsonString(json['merchant_sku'], 'merchant_sku'),
    unit: jsonString(json['unit'], 'unit'),
    availableQuantity: Decimal.parse(json['available_quantity'].toString()),
    unitPrice: Decimal.parse(json['unit_price'].toString()),
    leadTimeDays: jsonNumber(json['lead_time_days'], 'lead_time_days').toInt(),
  );

  final String id;
  final String productId;
  final String supplierSku;
  final String productName;
  final String merchantSku;
  final String unit;
  final Decimal availableQuantity;
  final Decimal unitPrice;
  final int leadTimeDays;
}

class SupplierDetail {
  const SupplierDetail({
    required this.id,
    required this.name,
    required this.adapterType,
    required this.isActive,
    required this.trustScore,
    required this.productCount,
    this.products = const [],
  });

  factory SupplierDetail.fromJson(JsonMap json) => SupplierDetail(
    id: jsonString(json['id'], 'id'),
    name: jsonString(json['name'], 'name'),
    adapterType: jsonString(json['adapter_type'], 'adapter_type'),
    isActive: jsonBool(json['is_active'], 'is_active'),
    trustScore: jsonNumber(json['trust_score'], 'trust_score').toDouble(),
    productCount: jsonNumber(json['product_count'], 'product_count').toInt(),
    products: json['products'] is List
        ? jsonList(json['products'])
              .map((item) => SupplierProduct.fromJson(jsonMap(item)))
              .toList(growable: false)
        : const [],
  );

  final String id;
  final String name;
  final String adapterType;
  final bool isActive;
  final double trustScore;
  final int productCount;
  final List<SupplierProduct> products;
}
