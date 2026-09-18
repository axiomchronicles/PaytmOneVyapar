import 'package:vyapar/core/networking/json.dart';

class AnalyticsOverview {
  const AnalyticsOverview({
    required this.salesQuantity,
    required this.lowInventoryProducts,
    required this.ordersByStatus,
  });

  factory AnalyticsOverview.fromJson(JsonMap json) {
    final rawOrders = json['orders_by_status'];
    final orders = rawOrders is Map
        ? jsonMap(rawOrders)
        : const <String, Object?>{};
    return AnalyticsOverview(
      salesQuantity: jsonNumber(
        json['sales_quantity'],
        'sales_quantity',
      ).toDouble(),
      lowInventoryProducts: jsonNumber(
        json['low_inventory_products'],
        'low_inventory_products',
      ).toInt(),
      ordersByStatus: orders.map(
        (key, value) => MapEntry(key, jsonNumber(value, key).toInt()),
      ),
    );
  }

  final double salesQuantity;
  final int lowInventoryProducts;
  final Map<String, int> ordersByStatus;

  int get totalOrders =>
      ordersByStatus.values.fold(0, (sum, value) => sum + value);
}
