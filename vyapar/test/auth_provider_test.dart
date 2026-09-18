import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/auth/auth_session.dart';
import 'package:vyapar/core/auth/auth_storage.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/features/auth/data/auth_repository.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({this.validationError, this.signInError})
    : super(Dio(), TokenStore(MemoryAuthStorage()));

  final AppFailure? validationError;
  final AppFailure? signInError;

  @override
  Future<void> validateSession() async {
    if (validationError case final error?) throw error;
  }

  @override
  Future<void> signIn({required String email, required String password}) async {
    if (signInError case final error?) throw error;
  }
}

void main() {
  test('unauthenticated when secure storage has no token', () async {
    final storage = MemoryAuthStorage();
    final container = ProviderContainer(
      overrides: [
        authStorageProvider.overrideWithValue(storage),
        tokenStoreProvider.overrideWithValue(TokenStore(storage)),
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
      ],
    );
    addTearDown(container.dispose);

    final session = await container.read(authControllerProvider.future);
    expect(session.status, AuthStatus.unauthenticated);
  });

  test('restores and validates a stored session', () async {
    final storage = MemoryAuthStorage('real-access-token');
    final container = ProviderContainer(
      overrides: [
        authStorageProvider.overrideWithValue(storage),
        tokenStoreProvider.overrideWithValue(TokenStore(storage)),
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
      ],
    );
    addTearDown(container.dispose);

    final session = await container.read(authControllerProvider.future);
    expect(session.status, AuthStatus.authenticated);
  });

  test(
    'expired restored session is cleared without entering the app',
    () async {
      const failure = AppFailure(
        kind: FailureKind.unauthorized,
        message: 'Invalid access token',
      );
      final storage = MemoryAuthStorage('expired-access-token');
      final tokens = TokenStore(storage);
      final container = ProviderContainer(
        overrides: [
          authStorageProvider.overrideWithValue(storage),
          tokenStoreProvider.overrideWithValue(tokens),
          authRepositoryProvider.overrideWithValue(
            _FakeAuthRepository(validationError: failure),
          ),
        ],
      );
      addTearDown(container.dispose);

      final session = await container.read(authControllerProvider.future);
      expect(session.status, AuthStatus.unauthenticated);
      expect(await storage.readAccessToken(), isNull);
    },
  );

  test('authentication failure remains visible as provider error', () async {
    final failure = AppFailure(
      kind: FailureKind.unauthorized,
      message: 'Invalid email or password',
    );
    final storage = MemoryAuthStorage();
    final container = ProviderContainer(
      overrides: [
        authStorageProvider.overrideWithValue(storage),
        tokenStoreProvider.overrideWithValue(TokenStore(storage)),
        authRepositoryProvider.overrideWithValue(
          _FakeAuthRepository(signInError: failure),
        ),
      ],
    );
    addTearDown(container.dispose);
    await container.read(authControllerProvider.future);

    await container
        .read(authControllerProvider.notifier)
        .signIn(email: 'merchant@example.com', password: 'wrong-password');

    expect(container.read(authControllerProvider).hasError, isTrue);
    expect(container.read(authControllerProvider).error, same(failure));
  });
}
