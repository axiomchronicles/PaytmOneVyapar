import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/core/auth/auth_storage.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/core/config/app_config.dart';
import 'package:vyapar/core/connectivity/connectivity_service.dart';
import 'package:vyapar/core/networking/dio_client.dart';

final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.current());

final authStorageProvider = Provider<AuthStorage>((ref) => SecureAuthStorage());

final tokenStoreProvider = Provider<TokenStore>(
  (ref) => TokenStore(ref.watch(authStorageProvider)),
);

class SessionEpoch extends Notifier<int> {
  @override
  int build() => 0;

  void expire() => state++;
}

final sessionEpochProvider = NotifierProvider<SessionEpoch, int>(
  SessionEpoch.new,
);

final dioProvider = Provider<Dio>((ref) {
  final tokenStore = ref.watch(tokenStoreProvider);
  return createDioClient(
    config: ref.watch(appConfigProvider),
    tokenStore: tokenStore,
    onUnauthorized: () async {
      await tokenStore.clear();
      ref.read(sessionEpochProvider.notifier).expire();
    },
  );
});

final connectivityServiceProvider = Provider<ConnectivityService>(
  (ref) => ConnectivityService(),
);

final isOnlineProvider = StreamProvider<bool>(
  (ref) => ref.watch(connectivityServiceProvider).online,
);
