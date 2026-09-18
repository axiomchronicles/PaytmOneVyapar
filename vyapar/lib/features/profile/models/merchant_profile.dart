import 'package:vyapar/core/networking/json.dart';

class StoreSummary {
  const StoreSummary({
    required this.id,
    required this.name,
    this.locality = 'Karol Bagh, New Delhi',
  });

  factory StoreSummary.fromJson(JsonMap json) => StoreSummary(
    id: jsonString(json['id'], 'id'),
    name: jsonString(json['name'], 'name'),
    locality: json['locality'] is String && (json['locality'] as String).isNotEmpty
        ? json['locality'] as String
        : 'Karol Bagh, New Delhi',
  );

  final String id;
  final String name;
  final String locality;
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

  String get initials {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2 && parts[0].isNotEmpty && parts[1].isNotEmpty) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    } else if (name.isNotEmpty) {
      return name.substring(0, name.length >= 2 ? 2 : 1).toUpperCase();
    }
    return 'RS';
  }
}
