import 'package:vyapar/core/networking/json.dart';

class Recommendation {
  const Recommendation({required this.sku, required this.score});

  factory Recommendation.fromJson(JsonMap json) => Recommendation(
    sku: jsonString(json['sku'], 'sku'),
    score: jsonNumber(json['score'], 'score').toDouble(),
  );

  final String sku;
  final double score;
}
