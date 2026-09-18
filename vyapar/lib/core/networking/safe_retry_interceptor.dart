import 'dart:async';

import 'package:dio/dio.dart';

class SafeRetryInterceptor extends Interceptor {
  SafeRetryInterceptor(this._dio, {this.maxRetries = 1});

  final Dio _dio;
  final int maxRetries;

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final request = err.requestOptions;
    final attempt = request.extra['safeRetryAttempt'] as int? ?? 0;
    final status = err.response?.statusCode;
    final transient =
        err.type == DioExceptionType.connectionError ||
        err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        (status != null && status >= 500);
    if (request.method.toUpperCase() != 'GET' ||
        !transient ||
        attempt >= maxRetries) {
      handler.next(err);
      return;
    }
    request.extra['safeRetryAttempt'] = attempt + 1;
    await Future<void>.delayed(Duration(milliseconds: 180 * (attempt + 1)));
    try {
      handler.resolve(await _dio.fetch<Object?>(request));
    } on DioException catch (nextError) {
      handler.next(nextError);
    }
  }
}
