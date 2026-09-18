import 'package:vyapar/core/auth/auth_storage.dart';

class TokenStore {
  TokenStore(this._storage);

  final AuthStorage _storage;
  String? _accessToken;

  String? get accessToken => _accessToken;

  Future<String?> restore() async {
    _accessToken = await _storage.readAccessToken();
    return _accessToken;
  }

  Future<void> save(String token) async {
    _accessToken = token;
    await _storage.writeAccessToken(token);
  }

  Future<void> clear() async {
    _accessToken = null;
    await _storage.clear();
  }
}
