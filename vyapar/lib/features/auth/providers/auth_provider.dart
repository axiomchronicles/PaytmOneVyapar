import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/auth/auth_session.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/features/auth/data/auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) =>
      AuthRepository(ref.watch(dioProvider), ref.watch(tokenStoreProvider)),
);

class AuthController extends AsyncNotifier<AuthSession> {
  @override
  Future<AuthSession> build() async {
    ref.watch(sessionEpochProvider);
    final token = await ref.watch(tokenStoreProvider).restore();
    if (token == null || token.isEmpty) {
      return const AuthSession.unauthenticated();
    }
    try {
      await ref.watch(authRepositoryProvider).validateSession();
      return const AuthSession.authenticated();
    } on AppFailure catch (failure) {
      if (failure.isUnauthorized) {
        await ref.read(tokenStoreProvider).clear();
        return const AuthSession.unauthenticated();
      }
      rethrow;
    }
  }

  Future<void> signIn({required String email, required String password}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await ref
          .read(authRepositoryProvider)
          .signIn(email: email, password: password);
      return const AuthSession.authenticated();
    });
  }

  Future<void> signOut() async {
    await ref.read(authRepositoryProvider).signOut();
    state = const AsyncData(AuthSession.unauthenticated());
  }

  Future<void> retryRestore() async => ref.invalidateSelf();
}

final authControllerProvider =
    AsyncNotifierProvider<AuthController, AuthSession>(AuthController.new);
