import 'package:vyapar/core/networking/json.dart';

class CursorPage<T> {
  const CursorPage({required this.items, this.nextCursor});

  factory CursorPage.fromJson(JsonMap json, T Function(JsonMap json) decode) =>
      CursorPage(
        items: jsonList(
          json['items'],
        ).map((item) => decode(jsonMap(item))).toList(growable: false),
        nextCursor: jsonOptionalString(json['next_cursor']),
      );

  final List<T> items;
  final String? nextCursor;

  bool get hasMore => nextCursor != null;

  CursorPage<T> append(CursorPage<T> next, String Function(T item) idOf) {
    final known = items.map(idOf).toSet();
    return CursorPage(
      items: [...items, ...next.items.where((item) => known.add(idOf(item)))],
      nextCursor: next.nextCursor,
    );
  }
}
