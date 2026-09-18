import 'package:vyapar/core/auth/auth_storage.dart';

class TokenStore {
  TokenStore(this._storage);

  final AuthStorage _storage;
  String? _accessToken;
  String? _refreshToken;

  String? get accessToken => _accessToken;
  String? get refreshToken => _refreshToken;

  Future<String?> restore() async {
    _accessToken = await _storage.readAccessToken();
    _refreshToken = await _storage.readRefreshToken();
    return _accessToken;
  }

  Future<void> save({
    required String accessToken,
    required String refreshToken,
  }) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
    await _storage.writeTokens(
      accessToken: accessToken,
      refreshToken: refreshToken,
    );
  }

  Future<void> clear() async {
    _accessToken = null;
    _refreshToken = null;
    await _storage.clear();
  }
}
