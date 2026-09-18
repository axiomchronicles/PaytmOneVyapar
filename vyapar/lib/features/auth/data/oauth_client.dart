import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import 'package:vyapar/features/auth/models/auth_models.dart';

abstract interface class MobileOAuthClient {
  Future<String?> authenticate(OAuthChallenge challenge);
}

class PlatformOAuthClient implements MobileOAuthClient {
  @override
  Future<String?> authenticate(OAuthChallenge challenge) async {
    if (challenge.provider == 'GOOGLE') {
      try {
        await GoogleSignIn.instance.initialize(
          clientId: challenge.clientId,
          serverClientId: challenge.clientId,
          nonce: challenge.nonce,
        );
        final account = await GoogleSignIn.instance.authenticate();
        return account.authentication.idToken;
      } on GoogleSignInException catch (error) {
        if (error.code == GoogleSignInExceptionCode.canceled) return null;
        rethrow;
      }
    }
    final available = await SignInWithApple.isAvailable();
    if (!available) {
      throw StateError('Apple Sign In is unavailable on this device.');
    }
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: const [AppleIDAuthorizationScopes.email],
        nonce: sha256.convert(utf8.encode(challenge.nonce)).toString(),
        state: challenge.state,
      );
      if (credential.state != null && credential.state != challenge.state) {
        throw StateError('Apple authorization state did not match.');
      }
      return credential.identityToken;
    } on SignInWithAppleAuthorizationException catch (error) {
      if (error.code == AuthorizationErrorCode.canceled) return null;
      rethrow;
    }
  }
}
