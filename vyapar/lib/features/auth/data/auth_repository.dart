import 'package:dio/dio.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';

class AuthRepository {
  AuthRepository(this._dio, this._tokens);

  final Dio _dio;
  final TokenStore _tokens;

  Future<void> signIn({required String email, required String password}) async {
    try {
      final response = await _dio.post<Object?>(
        '/auth/token',
        data: {'username': email.trim().toLowerCase(), 'password': password},
        options: Options(contentType: Headers.formUrlEncodedContentType),
      );
      final body = jsonMap(response.data);
      final token = jsonString(body['access_token'], 'access_token');
      await _tokens.save(token);
      await validateSession();
    } catch (error) {
      try {
        await _tokens.clear();
      } on Object {
        // Preserve the original authentication/network failure.
      }
      throw mapApiError(error);
    }
  }

  Future<void> validateSession() async {
    try {
      await _dio.get<Object?>('/merchants/me');
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<void> signOut() => _tokens.clear();
}
