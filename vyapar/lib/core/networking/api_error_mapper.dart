import 'package:dio/dio.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/core/networking/json.dart';

String? _validationMessage(JsonMap? envelope) {
  final details = envelope?['details'];
  if (details is! Map || details['errors'] is! List) return null;

  for (final error in details['errors'] as List) {
    if (error is! Map) continue;
    final message = jsonOptionalString(error['msg']);
    if (message == null || message.isEmpty) continue;
    final location = error['loc'];
    final field = location is List
        ? location.whereType<String>().where((part) => part != 'body').join('.')
        : '';
    return field.isEmpty ? message : '$field: $message';
  }
  return null;
}

AppFailure mapApiError(Object error) {
  if (error is AppFailure) return error;
  if (error is DioException) {
    if (error.type == DioExceptionType.cancel) {
      return const AppFailure(
        kind: FailureKind.unexpected,
        message: 'Request cancelled.',
        code: 'REQUEST_CANCELLED',
      );
    }
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.sendTimeout) {
      return const AppFailure(
        kind: FailureKind.timeout,
        message: 'The server took too long to respond. Please try again.',
        code: 'TIMEOUT',
      );
    }
    if (error.type == DioExceptionType.connectionError) {
      return const AppFailure(
        kind: FailureKind.offline,
        message:
            'No connection to Vyapar. Check your internet and backend URL.',
        code: 'CONNECTION_FAILED',
      );
    }
    final status = error.response?.statusCode;
    final serverFailure = status != null && status >= 500;
    final body = error.response?.data;
    JsonMap? envelope;
    if (body is Map) {
      final root = jsonMap(body);
      if (root['error'] is Map) envelope = jsonMap(root['error']);
    }
    final code = jsonOptionalString(envelope?['code']);
    final message =
        (status == 422 ? _validationMessage(envelope) : null) ??
        jsonOptionalString(envelope?['message']) ??
        (serverFailure
            ? 'Vyapar is temporarily unavailable.'
            : switch (status) {
                401 => 'Your session has expired. Please sign in again.',
                403 => 'You do not have permission for this action.',
                404 => 'The requested record was not found.',
                409 =>
                  'This item changed on the server. Refresh and try again.',
                422 => 'Please check the entered information.',
                429 => 'Too many requests. Please wait a moment.',
                _ => 'The request could not be completed.',
              });
    return AppFailure(
      kind: serverFailure
          ? FailureKind.unavailable
          : switch (status) {
              401 => FailureKind.unauthorized,
              403 => FailureKind.forbidden,
              404 => FailureKind.notFound,
              409 => FailureKind.conflict,
              422 => FailureKind.validation,
              429 => FailureKind.provider,
              _ => FailureKind.unexpected,
            },
      message: message,
      code: code,
      requestId: jsonOptionalString(envelope?['request_id']),
      details: envelope?['details'] is Map
          ? jsonMap(envelope?['details'])
          : const <String, Object?>{},
    );
  }
  if (error is FormatException) {
    return const AppFailure(
      kind: FailureKind.unexpected,
      message: 'Vyapar received an unexpected server response.',
      code: 'INVALID_RESPONSE',
    );
  }
  return const AppFailure(
    kind: FailureKind.unexpected,
    message: 'The request could not be completed.',
  );
}
