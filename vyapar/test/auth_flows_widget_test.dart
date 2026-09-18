import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/core/auth/auth_storage.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/design_system/theme/app_theme.dart';
import 'package:vyapar/features/auth/data/auth_repository.dart';
import 'package:vyapar/features/auth/data/oauth_client.dart';
import 'package:vyapar/features/auth/models/auth_models.dart';
import 'package:vyapar/features/auth/presentation/otp_screen.dart';
import 'package:vyapar/features/auth/presentation/registration_screen.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class _OtpState extends OtpFlowController {
  @override
  Future<OtpChallenge?> build() async => OtpChallenge(
    id: 'challenge-id',
    destination: '••••••3210',
    expiresAt: DateTime(2026, 9, 18, 12, 5),
    resendAvailableAt: DateTime(2026, 9, 18, 12, 1),
  );

  @override
  Future<bool> verify(String otp, {String? phone}) async => false;
}

class _PendingRegistration extends PendingRegistrationController {
  @override
  PendingRegistration? build() => const PendingRegistration(
    token: 'verified-registration-token',
    phone: '9876543210',
  );
}

class _RegistrationState extends RegistrationController {
  @override
  Future<void> build() async {}

  @override
  Future<void> register({
    required String email,
    required String businessName,
    required String storeName,
    String? password,
  }) async {}
}

class _OAuthRepository extends AuthRepository {
  _OAuthRepository() : super(Dio(), TokenStore(MemoryAuthStorage()));

  @override
  Future<OAuthChallenge> startOAuth(String provider) async => OAuthChallenge(
    id: 'challenge-id',
    provider: provider.toUpperCase(),
    state: 'server-state-value',
    nonce: 'server-nonce-value',
    clientId: 'public-client-id',
  );

  @override
  Future<AuthExchangeResult> exchangeOAuth({
    required OAuthChallenge challenge,
    required String idToken,
  }) async => const AuthExchangeResult(
    registrationRequired: true,
    registrationToken: 'oauth-registration-token',
    email: 'owner@example.com',
  );
}

class _OAuthClient implements MobileOAuthClient {
  OAuthChallenge? challenge;

  @override
  Future<String?> authenticate(OAuthChallenge challenge) async {
    this.challenge = challenge;
    return 'provider-id-token';
  }
}

Widget _app(Widget child) => MaterialApp(theme: AppTheme.light, home: child);

void main() {
  testWidgets('OTP screen renders a server-issued challenge', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [otpFlowProvider.overrideWith(_OtpState.new)],
        child: _app(const OtpScreen(registration: false)),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('3210'), findsOneWidget);
    expect(find.byKey(const ValueKey('otp_input')), findsOneWidget);
    expect(find.byKey(const ValueKey('verify_otp_button')), findsOneWidget);
  });

  testWidgets('registration requires verified state and business fields', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          pendingRegistrationProvider.overrideWith(_PendingRegistration.new),
          registrationControllerProvider.overrideWith(_RegistrationState.new),
        ],
        child: _app(const RegistrationScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('registration_email')), findsOneWidget);
    expect(find.byKey(const ValueKey('registration_business')), findsOneWidget);
    expect(find.byKey(const ValueKey('registration_store')), findsOneWidget);
    expect(find.byKey(const ValueKey('registration_password')), findsOneWidget);
  });

  test(
    'OAuth flow preserves server state and creates registration state',
    () async {
      final client = _OAuthClient();
      final container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(_OAuthRepository()),
          mobileOAuthClientProvider.overrideWithValue(client),
        ],
      );
      addTearDown(container.dispose);
      await container.read(oauthFlowProvider.future);

      final needsRegistration = await container
          .read(oauthFlowProvider.notifier)
          .authenticate('google');

      expect(needsRegistration, isTrue);
      expect(client.challenge?.state, 'server-state-value');
      expect(
        container.read(pendingRegistrationProvider)?.email,
        'owner@example.com',
      );
    },
  );
}
