import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/recommendations/data/recommendation_repository.dart';
import 'package:vyapar/features/recommendations/models/recommendation.dart';

final recommendationRepositoryProvider = Provider<RecommendationRepository>(
  (ref) => RecommendationRepository(ref.watch(dioProvider)),
);

class RecommendationController extends AsyncNotifier<List<Recommendation>> {
  @override
  Future<List<Recommendation>> build() =>
      ref.watch(recommendationRepositoryProvider).list();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(recommendationRepositoryProvider).list(),
    );
  }
}

final recommendationControllerProvider =
    AsyncNotifierProvider<RecommendationController, List<Recommendation>>(
      RecommendationController.new,
    );

final recommendationDetailProvider = Provider.autoDispose
    .family<Recommendation?, String>((ref, sku) {
      final values =
          ref.watch(recommendationControllerProvider).value ?? const [];
      for (final recommendation in values) {
        if (recommendation.sku == sku) return recommendation;
      }
      return null;
    });
