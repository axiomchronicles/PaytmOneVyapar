import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/core/networking/realtime_event.dart';
import 'package:vyapar/core/networking/realtime_router.dart';
import 'package:vyapar/core/networking/websocket_client.dart';

void main() {
  test('decodes versioned outbox envelope and suppresses duplicates', () {
    final event = RealtimeEvent.fromJson(
      jsonMap({
        'event_id': 'event-1',
        'event_type': 'ORDER_EXECUTED',
        'aggregate_type': 'order',
        'aggregate_id': 'order-1',
        'occurred_at': '2026-09-18T10:00:00Z',
        'correlation_id': 'request-1',
        'payload': {'order_id': 'order-1', 'status': 'CONFIRMED'},
        'version': 1,
      }),
    );
    final deduplicator = RealtimeEventDeduplicator(capacity: 2);

    expect(event.type, 'ORDER_EXECUTED');
    expect(event.data['status'], 'CONFIRMED');
    expect(deduplicator.accept(event.eventId), isTrue);
    expect(deduplicator.accept(event.eventId), isFalse);
  });

  test(
    'out-of-order domain updates route to authoritative refetch targets',
    () {
      final newer = RealtimeEventRouter.targets('ORDER_EXECUTED');
      final older = RealtimeEventRouter.targets('ORDER_FAILED');

      expect(newer, contains(RealtimeTarget.orders));
      expect(older, contains(RealtimeTarget.orders));
      expect(newer, contains(RealtimeTarget.analytics));
      expect(RealtimeEventRouter.targets('REALTIME_RESYNC_REQUIRED'), {
        RealtimeTarget.all,
      });
    },
  );
}
