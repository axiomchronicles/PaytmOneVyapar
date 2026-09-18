import 'dart:async';

import 'package:dio/dio.dart';
import 'package:vyapar/core/auth/token_store.dart';

class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._tokens, this._onUnauthorized);

  final TokenStore _tokens;
  final FutureOr<void> Function() _onUnauthorized;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _tokens.accessToken;
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.response?.statusCode == 401 &&
        !err.requestOptions.path.endsWith('/auth/token')) {
      unawaited(Future<void>.sync(_onUnauthorized));
    }
    handler.next(err);
  }
}
