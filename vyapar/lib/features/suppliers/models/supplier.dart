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
    this.phoneNumber,
    this.gstin,
    this.city,
    this.state,
    this.pincode,
    this.category,
    this.products = const [],
  });

  factory SupplierDetail.fromJson(JsonMap json) => SupplierDetail(
    id: jsonString(json['id'], 'id'),
    name: jsonString(json['name'], 'name'),
    adapterType: jsonString(json['adapter_type'], 'adapter_type'),
    isActive: jsonBool(json['is_active'], 'is_active'),
    trustScore: jsonNumber(json['trust_score'], 'trust_score').toDouble(),
    productCount: jsonNumber(json['product_count'], 'product_count').toInt(),
    phoneNumber: jsonOptionalString(json['phone_number']),
    gstin: jsonOptionalString(json['gstin']),
    city: jsonOptionalString(json['city']),
    state: jsonOptionalString(json['state']),
    pincode: jsonOptionalString(json['pincode']),
    category: jsonOptionalString(json['category']),
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
  final String? phoneNumber;
  final String? gstin;
  final String? city;
  final String? state;
  final String? pincode;
  final String? category;
  final List<SupplierProduct> products;
}

class NearbySupplier {
  const NearbySupplier({
    required this.id,
    required this.name,
    this.city,
    this.state,
    this.pincode,
    this.locality,
    this.distanceKm,
    this.trustScore = 0.95,
    this.productCount = 0,
    this.phoneNumber,
    this.category,
  });

  factory NearbySupplier.fromJson(JsonMap json) => NearbySupplier(
    id: jsonString(json['id'], 'id'),
    name: jsonString(json['name'], 'name'),
    city: jsonOptionalString(json['city']),
    state: jsonOptionalString(json['state']),
    pincode: jsonOptionalString(json['pincode']),
    locality: jsonOptionalString(json['locality']),
    distanceKm: json['distance_km'] != null
        ? jsonNumber(json['distance_km'], 'distance_km').toDouble()
        : null,
    trustScore: json['trust_score'] != null
        ? jsonNumber(json['trust_score'], 'trust_score').toDouble()
        : 0.95,
    productCount: json['product_count'] != null
        ? jsonNumber(json['product_count'], 'product_count').toInt()
        : 0,
    phoneNumber: jsonOptionalString(json['phone_number']),
    category: jsonOptionalString(json['category']),
  );

  final String id;
  final String name;
  final String? city;
  final String? state;
  final String? pincode;
  final String? locality;
  final double? distanceKm;
  final double trustScore;
  final int productCount;
  final String? phoneNumber;
  final String? category;
}

class NearbyMerchant {
  const NearbyMerchant({
    required this.id,
    required this.name,
    this.city,
    this.state,
    this.pincode,
    this.locality,
    this.distanceKm,
    this.productCount = 0,
    this.phoneNumber,
    this.businessType = 'retail',
  });

  factory NearbyMerchant.fromJson(JsonMap json) => NearbyMerchant(
    id: jsonString(json['id'], 'id'),
    name: jsonString(json['name'], 'name'),
    city: jsonOptionalString(json['city']),
    state: jsonOptionalString(json['state']),
    pincode: jsonOptionalString(json['pincode']),
    locality: jsonOptionalString(json['locality']),
    distanceKm: json['distance_km'] != null
        ? jsonNumber(json['distance_km'], 'distance_km').toDouble()
        : null,
    productCount: json['product_count'] != null
        ? jsonNumber(json['product_count'], 'product_count').toInt()
        : 0,
    phoneNumber: jsonOptionalString(json['phone_number']),
    businessType: jsonOptionalString(json['business_type']) ?? 'retail',
  );

  final String id;
  final String name;
  final String? city;
  final String? state;
  final String? pincode;
  final String? locality;
  final double? distanceKm;
  final int productCount;
  final String? phoneNumber;
  final String businessType;
}
