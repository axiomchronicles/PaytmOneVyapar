import 'package:vyapar/core/networking/json.dart';

class OpportunityItem {
  const OpportunityItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.actionType,
    this.icon = 'chart',
  });

  factory OpportunityItem.fromJson(JsonMap json) => OpportunityItem(
    id: json['id']?.toString() ?? '',
    title: json['title']?.toString() ?? '',
    subtitle: json['subtitle']?.toString() ?? '',
    actionLabel: json['action_label']?.toString() ?? 'View',
    actionType: json['action_type']?.toString() ?? 'deal',
    icon: json['icon']?.toString() ?? 'chart',
  );

  final String id;
  final String title;
  final String subtitle;
  final String actionLabel;
  final String actionType;
  final String icon;
}

class CriticalAlert {
  const CriticalAlert({
    required this.title,
    required this.description,
    this.tag = 'Dhyaan dene layak',
    this.sku = 'COLD-COLA-300',
    this.actionLabel = 'Review',
    this.actionUrl = '/recommendations',
  });

  factory CriticalAlert.fromJson(JsonMap json) => CriticalAlert(
    title: json['title']?.toString() ?? '',
    description: json['description']?.toString() ?? '',
    tag: json['tag']?.toString() ?? 'Dhyaan dene layak',
    sku: json['sku']?.toString() ?? 'COLD-COLA-300',
    actionLabel: json['action_label']?.toString() ?? 'Review',
    actionUrl: json['action_url']?.toString() ?? '/recommendations',
  );

  final String title;
  final String description;
  final String tag;
  final String sku;
  final String actionLabel;
  final String actionUrl;
}

class AnalyticsOverview {
  const AnalyticsOverview({
    required this.salesQuantity,
    required this.lowInventoryProducts,
    required this.ordersByStatus,
    this.totalSalesAmount = 18420.0,
    this.salesGrowthPct = 12.0,
    this.customerCount = 146,
    this.customerGrowthPct = 8.0,
    this.expectedSettlement = 17980.0,
    this.criticalAlert,
    this.opportunities = const [],
  });

  factory AnalyticsOverview.fromJson(JsonMap json) {
    final rawOrders = json['orders_by_status'];
    final orders = rawOrders is Map
        ? jsonMap(rawOrders)
        : const <String, Object?>{};

    CriticalAlert? alert;
    if (json['critical_alert'] is Map) {
      alert = CriticalAlert.fromJson(jsonMap(json['critical_alert']));
    }

    final rawOpps = json['opportunities'];
    final opportunities = rawOpps is List
        ? rawOpps
            .whereType<Map<Object?, Object?>>()
            .map((item) => OpportunityItem.fromJson(jsonMap(item)))
            .toList(growable: false)
        : const <OpportunityItem>[];

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
      totalSalesAmount: json['total_sales_amount'] != null
          ? jsonNumber(json['total_sales_amount'], 'total_sales_amount').toDouble()
          : 18420.0,
      salesGrowthPct: json['sales_growth_pct'] != null
          ? jsonNumber(json['sales_growth_pct'], 'sales_growth_pct').toDouble()
          : 12.0,
      customerCount: json['customer_count'] != null
          ? jsonNumber(json['customer_count'], 'customer_count').toInt()
          : 146,
      customerGrowthPct: json['customer_growth_pct'] != null
          ? jsonNumber(json['customer_growth_pct'], 'customer_growth_pct').toDouble()
          : 8.0,
      expectedSettlement: json['expected_settlement'] != null
          ? jsonNumber(json['expected_settlement'], 'expected_settlement').toDouble()
          : 17980.0,
      criticalAlert: alert,
      opportunities: opportunities,
    );
  }

  final double salesQuantity;
  final int lowInventoryProducts;
  final Map<String, int> ordersByStatus;
  final double totalSalesAmount;
  final double salesGrowthPct;
  final int customerCount;
  final double customerGrowthPct;
  final double expectedSettlement;
  final CriticalAlert? criticalAlert;
  final List<OpportunityItem> opportunities;

  int get totalOrders =>
      ordersByStatus.values.fold(0, (sum, value) => sum + value);
}
