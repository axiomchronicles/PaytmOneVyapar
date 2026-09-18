import 'package:vyapar/core/networking/json.dart';

class StoreSummary {
  const StoreSummary({required this.id, required this.name});

  factory StoreSummary.fromJson(JsonMap json) => StoreSummary(
    id: jsonString(json['id'], 'id'),
    name: jsonString(json['name'], 'name'),
  );

  final String id;
  final String name;
}

class MerchantProfile {
  const MerchantProfile({
    required this.id,
    required this.name,
    required this.currency,
    required this.spendingLimit,
    required this.stores,
  });

  factory MerchantProfile.fromJson(JsonMap json) => MerchantProfile(
    id: jsonString(json['id'], 'id'),
    name: jsonString(json['name'], 'name'),
    currency: jsonString(json['currency'], 'currency'),
    spendingLimit: jsonNumber(
      json['spending_limit'],
      'spending_limit',
    ).toDouble(),
    stores: jsonList(json['stores'])
        .map((item) => StoreSummary.fromJson(jsonMap(item)))
        .toList(growable: false),
  );

  final String id;
  final String name;
  final String currency;
  final double spendingLimit;
  final List<StoreSummary> stores;
}
