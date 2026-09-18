import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/realtime_event.dart';
import 'package:vyapar/core/networking/websocket_client.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

final realtimeEventsProvider = StreamProvider<RealtimeEvent>((ref) async* {
  final session = await ref.watch(authControllerProvider.future);
  final token = ref.watch(tokenStoreProvider).accessToken;
  if (!session.isAuthenticated || token == null) return;
  final client = RealtimeClient(
    config: ref.watch(appConfigProvider),
    token: token,
  );
  ref.onDispose(() => unawaited(client.close()));
  yield* client.events();
});
