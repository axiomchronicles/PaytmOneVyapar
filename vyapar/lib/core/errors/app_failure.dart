enum FailureKind {
  unauthorized,
  forbidden,
  notFound,
  conflict,
  validation,
  offline,
  timeout,
  provider,
  unavailable,
  unexpected,
}

class AppFailure implements Exception {
  const AppFailure({
    required this.kind,
    required this.message,
    this.code,
    this.requestId,
    this.details = const <String, Object?>{},
  });

  final FailureKind kind;
  final String message;
  final String? code;
  final String? requestId;
  final Map<String, Object?> details;

  bool get isUnauthorized => kind == FailureKind.unauthorized;

  @override
  String toString() => message;
}
