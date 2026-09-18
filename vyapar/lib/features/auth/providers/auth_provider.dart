import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/auth/auth_session.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/features/auth/data/auth_repository.dart';
import 'package:vyapar/features/auth/data/oauth_client.dart';
import 'package:vyapar/features/auth/models/auth_models.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) =>
      AuthRepository(ref.watch(dioProvider), ref.watch(tokenStoreProvider)),
);

final mobileOAuthClientProvider = Provider<MobileOAuthClient>(
  (ref) => PlatformOAuthClient(),
);

class PendingRegistration {
  const PendingRegistration({
    required this.token,
    this.email,
    this.phone,
    this.oauth = false,
  });

  final String token;
  final String? email;
  final String? phone;
  final bool oauth;
}

class PendingRegistrationController extends Notifier<PendingRegistration?> {
  @override
  PendingRegistration? build() => null;

  void set(PendingRegistration value) => state = value;
  void clear() => state = null;
}

final pendingRegistrationProvider =
    NotifierProvider<PendingRegistrationController, PendingRegistration?>(
      PendingRegistrationController.new,
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

  void authenticated() => state = const AsyncData(AuthSession.authenticated());

  Future<void> retryRestore() async => ref.invalidateSelf();
}

final authControllerProvider =
    AsyncNotifierProvider<AuthController, AuthSession>(AuthController.new);

class OtpFlowController extends AsyncNotifier<OtpChallenge?> {
  @override
  Future<OtpChallenge?> build() async => null;

  Future<void> request(String phone, {required bool registration}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(authRepositoryProvider)
          .requestOtp(phone, registration: registration),
    );
  }

  Future<bool> verify(String otp, {String? phone}) async {
    final challenge = state.value;
    if (challenge == null) return false;
    state = const AsyncLoading();
    try {
      final result = await ref
          .read(authRepositoryProvider)
          .verifyOtp(challengeId: challenge.id, otp: otp);
      if (result.registrationRequired) {
        ref
            .read(pendingRegistrationProvider.notifier)
            .set(
              PendingRegistration(
                token: result.registrationToken!,
                phone: phone,
              ),
            );
        state = AsyncData(challenge);
        return true;
      }
      ref.read(authControllerProvider.notifier).authenticated();
      state = AsyncData(challenge);
      return false;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }

  Future<void> resend() async {
    final challenge = state.value;
    if (challenge == null) return;
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).resendOtp(challenge.id),
    );
  }
}

final otpFlowProvider = AsyncNotifierProvider<OtpFlowController, OtpChallenge?>(
  OtpFlowController.new,
);

class OAuthFlowController extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<bool?> authenticate(String provider) async {
    state = const AsyncLoading();
    try {
      final repository = ref.read(authRepositoryProvider);
      final challenge = await repository.startOAuth(provider);
      final idToken = await ref
          .read(mobileOAuthClientProvider)
          .authenticate(challenge);
      if (idToken == null) {
        state = const AsyncData(null);
        return null;
      }
      final result = await repository.exchangeOAuth(
        challenge: challenge,
        idToken: idToken,
      );
      if (result.registrationRequired) {
        ref
            .read(pendingRegistrationProvider.notifier)
            .set(
              PendingRegistration(
                token: result.registrationToken!,
                email: result.email,
                oauth: true,
              ),
            );
        state = const AsyncData(null);
        return true;
      }
      ref.read(authControllerProvider.notifier).authenticated();
      state = const AsyncData(null);
      return false;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }
}

final oauthFlowProvider = AsyncNotifierProvider<OAuthFlowController, void>(
  OAuthFlowController.new,
);

class RegistrationController extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> register({
    required String email,
    required String businessName,
    required String storeName,
    String? password,
  }) async {
    final pending = ref.read(pendingRegistrationProvider);
    if (pending == null) throw StateError('Verification is required.');
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await ref
          .read(authRepositoryProvider)
          .register(
            email: email,
            businessName: businessName,
            storeName: storeName,
            registrationToken: pending.token,
            password: pending.oauth ? null : password,
            phone: pending.phone,
          );
      ref.read(pendingRegistrationProvider.notifier).clear();
      ref.read(authControllerProvider.notifier).authenticated();
    });
  }
}

final registrationControllerProvider =
    AsyncNotifierProvider<RegistrationController, void>(
      RegistrationController.new,
    );
