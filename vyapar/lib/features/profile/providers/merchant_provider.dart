import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/profile/data/merchant_repository.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';

final merchantRepositoryProvider = Provider<MerchantRepository>(
  (ref) => MerchantRepository(ref.watch(dioProvider)),
);

class MerchantController extends AsyncNotifier<MerchantProfile> {
  @override
  Future<MerchantProfile> build() =>
      ref.watch(merchantRepositoryProvider).getProfile();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(merchantRepositoryProvider).getProfile(),
    );
  }
}

final merchantControllerProvider =
    AsyncNotifierProvider<MerchantController, MerchantProfile>(
      MerchantController.new,
    );

class SelectedStore extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String? storeId) => state = storeId;
}

final selectedStoreProvider = NotifierProvider<SelectedStore, String?>(
  SelectedStore.new,
);
