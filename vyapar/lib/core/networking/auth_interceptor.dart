import 'dart:async';

import 'package:dio/dio.dart';
import 'package:vyapar/core/auth/token_store.dart';

class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._tokens, this._onUnauthorized, this._refreshClient);

  final TokenStore _tokens;
  final FutureOr<void> Function() _onUnauthorized;
  final Dio _refreshClient;
  Future<bool>? _refreshing;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _tokens.accessToken;
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401 &&
        !err.requestOptions.path.contains('/auth/')) {
      final refreshToken = _tokens.refreshToken;
      if (refreshToken != null && refreshToken.isNotEmpty) {
        final refreshed = await (_refreshing ??= _refresh(refreshToken));
        _refreshing = null;
        final accessToken = _tokens.accessToken;
        if (refreshed && accessToken != null) {
          err.requestOptions.headers['Authorization'] = 'Bearer $accessToken';
          try {
            handler.resolve(
              await _refreshClient.fetch<Object?>(err.requestOptions),
            );
            return;
          } on DioException catch (retryError) {
            handler.next(retryError);
            return;
          }
        }
      }
      await Future<void>.sync(_onUnauthorized);
    }
    handler.next(err);
  }

  Future<bool> _refresh(String refreshToken) async {
    try {
      final response = await _refreshClient.post<Object?>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final body = response.data;
      if (body is! Map) return false;
      final access = body['access_token'];
      final refresh = body['refresh_token'];
      if (access is! String || refresh is! String) return false;
      await _tokens.save(accessToken: access, refreshToken: refresh);
      return true;
    } on Object {
      return false;
    }
  }
}
