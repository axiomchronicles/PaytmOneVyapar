typedef JsonMap = Map<String, Object?>;

JsonMap jsonMap(Object? value) {
  if (value is! Map) {
    throw const FormatException('Expected a JSON object');
  }
  return value.map((key, item) => MapEntry(key.toString(), item));
}

List<Object?> jsonList(Object? value) {
  if (value is! List) {
    throw const FormatException('Expected a JSON array');
  }
  return List<Object?>.from(value);
}

String jsonString(Object? value, String key) {
  if (value is String) return value;
  throw FormatException('Expected string for $key');
}

String? jsonOptionalString(Object? value) => value is String ? value : null;

num jsonNumber(Object? value, String key) {
  if (value is num) return value;
  if (value is String) {
    final parsed = num.tryParse(value);
    if (parsed != null) return parsed;
  }
  throw FormatException('Expected number for $key');
}

bool jsonBool(Object? value, String key) {
  if (value is bool) return value;
  throw FormatException('Expected boolean for $key');
}
