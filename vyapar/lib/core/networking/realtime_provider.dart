import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/realtime_event.dart';
import 'package:vyapar/core/networking/websocket_client.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class RealtimeForeground extends Notifier<bool> {
  @override
  bool build() => true;

  void setForeground(bool value) => state = value;
}

final realtimeForegroundProvider = NotifierProvider<RealtimeForeground, bool>(
  RealtimeForeground.new,
);

final realtimeEventsProvider = StreamProvider<RealtimeEvent>((ref) async* {
  if (!ref.watch(realtimeForegroundProvider)) return;
  final session = await ref.watch(authControllerProvider.future);
  final token = ref.watch(tokenStoreProvider).accessToken;
  if (!session.isAuthenticated || token == null) return;
  final client = RealtimeCoordinator(
    config: ref.watch(appConfigProvider),
    token: token,
  );
  ref.onDispose(() => unawaited(client.close()));
  yield* client.events();
});
