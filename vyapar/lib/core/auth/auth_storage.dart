import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract interface class AuthStorage {
  Future<String?> readAccessToken();
  Future<String?> readRefreshToken();
  Future<void> writeTokens({
    required String accessToken,
    required String refreshToken,
  });
  Future<void> clear();
}

class SecureAuthStorage implements AuthStorage {
  SecureAuthStorage([FlutterSecureStorage? storage])
    : _storage = storage ?? _platformStorage();

  static FlutterSecureStorage _platformStorage() =>
      defaultTargetPlatform == TargetPlatform.macOS
      ? const FlutterSecureStorage(
          mOptions: MacOsOptions(usesDataProtectionKeychain: false),
        )
      : const FlutterSecureStorage();

  static const _accessTokenKey = 'vyapar_access_token';
  static const _refreshTokenKey = 'vyapar_refresh_token';
  final FlutterSecureStorage _storage;

  @override
  Future<String?> readAccessToken() => _storage.read(key: _accessTokenKey);

  @override
  Future<String?> readRefreshToken() => _storage.read(key: _refreshTokenKey);

  @override
  Future<void> writeTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }
}

class MemoryAuthStorage implements AuthStorage {
  MemoryAuthStorage([this.token, this.refreshToken]);

  String? token;
  String? refreshToken;

  @override
  Future<void> clear() async {
    token = null;
    refreshToken = null;
  }

  @override
  Future<String?> readAccessToken() async => token;

  @override
  Future<String?> readRefreshToken() async => refreshToken;

  @override
  Future<void> writeTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    token = accessToken;
    this.refreshToken = refreshToken;
  }
}
