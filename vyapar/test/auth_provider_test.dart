import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/auth/auth_session.dart';
import 'package:vyapar/core/auth/auth_storage.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/features/auth/data/auth_repository.dart';
import 'package:vyapar/features/auth/models/auth_models.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({this.validationError, this.signInError})
    : super(Dio(), TokenStore(MemoryAuthStorage()));

  final AppFailure? validationError;
  final AppFailure? signInError;

  @override
  Future<UserMe> validateSession() async {
    if (validationError case final error?) throw error;
    return const UserMe(
      userId: 'test-user-id',
      merchantId: 'test-merchant-id',
      role: 'merchant',
      accountType: 'merchant',
      email: 'test@vyapaar.local',
      businessName: 'Test Kirana',
    );
  }

  @override
  Future<void> signIn({required String email, required String password}) async {
    if (signInError case final error?) throw error;
  }
}

class _SupplierOtpAuthRepository extends AuthRepository {
  _SupplierOtpAuthRepository() : super(Dio(), TokenStore(MemoryAuthStorage()));

  @override
  Future<OtpChallenge> requestOtp(
    String phone, {
    required bool registration,
  }) async => OtpChallenge(
    id: 'supplier-otp-challenge',
    destination: phone,
    expiresAt: DateTime(2026, 9, 20),
    resendAvailableAt: DateTime(2026, 9, 19),
  );

  @override
  Future<AuthExchangeResult> verifyOtp({
    required String challengeId,
    required String otp,
  }) async => const AuthExchangeResult(registrationRequired: false);

  @override
  Future<UserMe> validateSession() async => const UserMe(
    userId: 'supplier-user-id',
    merchantId: 'supplier-business-id',
    role: 'supplier',
    accountType: 'supplier',
    email: 'supplier@vyapaar.local',
    businessName: 'Metro Wholesale',
  );
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

  test('OTP sign-in retains the supplier role before navigation', () async {
    final storage = MemoryAuthStorage();
    final container = ProviderContainer(
      overrides: [
        authStorageProvider.overrideWithValue(storage),
        tokenStoreProvider.overrideWithValue(TokenStore(storage)),
        authRepositoryProvider.overrideWithValue(_SupplierOtpAuthRepository()),
      ],
    );
    addTearDown(container.dispose);
    await container.read(authControllerProvider.future);
    await container.read(otpFlowProvider.future);

    await container
        .read(otpFlowProvider.notifier)
        .request('919999999999', registration: false);
    final needsRegistration = await container
        .read(otpFlowProvider.notifier)
        .verify('123456', phone: '919999999999');

    expect(needsRegistration, isFalse);
    expect(container.read(authControllerProvider).value?.role, 'supplier');
    expect(container.read(authControllerProvider).value?.isSupplier, isTrue);
  });
}
