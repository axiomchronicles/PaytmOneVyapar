import 'package:decimal/decimal.dart';
import 'package:vyapar/core/networking/json.dart';

enum AnalyticsMetric { sales, inventory, procurement }

class AnalyticsDatum {
  const AnalyticsDatum({
    required this.label,
    required this.value,
    this.entityId,
  });

  final String label;
  final Decimal value;
  final String? entityId;
}

class AnalyticsDetail {
  const AnalyticsDetail({required this.metric, required this.points});

  factory AnalyticsDetail.fromJson(AnalyticsMetric metric, JsonMap json) {
    final source = switch (metric) {
      AnalyticsMetric.sales => json['points'],
      AnalyticsMetric.inventory => json['categories'],
      AnalyticsMetric.procurement => json['suppliers'],
    };
    final rows = source is List ? jsonList(source) : const <Object?>[];
    return AnalyticsDetail(
      metric: metric,
      points: rows
          .map((raw) {
            final item = jsonMap(raw);
            return switch (metric) {
              AnalyticsMetric.sales => AnalyticsDatum(
                label: jsonString(item['bucket'], 'bucket'),
                value: Decimal.parse(item['value'].toString()),
              ),
              AnalyticsMetric.inventory => AnalyticsDatum(
                label: jsonString(item['category'], 'category'),
                value: Decimal.parse(item['low_products'].toString()),
              ),
              AnalyticsMetric.procurement => AnalyticsDatum(
                label: jsonString(item['supplier_name'], 'supplier_name'),
                value: Decimal.parse(item['spend'].toString()),
                entityId: jsonOptionalString(item['supplier_id']),
              ),
            };
          })
          .toList(growable: false),
    );
  }

  final AnalyticsMetric metric;
  final List<AnalyticsDatum> points;
}
