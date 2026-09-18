import 'dart:async';

import 'package:dio/dio.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/core/config/app_config.dart';
import 'package:vyapar/core/networking/auth_interceptor.dart';
import 'package:vyapar/core/networking/request_id_interceptor.dart';
import 'package:vyapar/core/networking/safe_retry_interceptor.dart';

Dio createDioClient({
  required AppConfig config,
  required TokenStore tokenStore,
  required FutureOr<void> Function() onUnauthorized,
}) {
  final options = BaseOptions(
    baseUrl: config.apiBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    sendTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 20),
    responseType: ResponseType.json,
    headers: const {'Accept': 'application/json'},
  );
  final dio = Dio(options);
  final refreshClient = Dio(options);
  dio.interceptors.addAll([
    RequestIdInterceptor(),
    AuthInterceptor(tokenStore, onUnauthorized, refreshClient),
    SafeRetryInterceptor(dio),
  ]);
  return dio;
}
