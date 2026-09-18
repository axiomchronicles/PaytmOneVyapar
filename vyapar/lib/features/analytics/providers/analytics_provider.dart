import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/analytics/data/analytics_repository.dart';
import 'package:vyapar/features/analytics/models/analytics_overview.dart';

final analyticsRepositoryProvider = Provider<AnalyticsRepository>(
  (ref) => AnalyticsRepository(ref.watch(dioProvider)),
);

class AnalyticsController extends AsyncNotifier<AnalyticsOverview> {
  @override
  Future<AnalyticsOverview> build() =>
      ref.watch(analyticsRepositoryProvider).getOverview();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(analyticsRepositoryProvider).getOverview(),
    );
  }
}

final analyticsControllerProvider =
    AsyncNotifierProvider<AnalyticsController, AnalyticsOverview>(
      AnalyticsController.new,
    );
