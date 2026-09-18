import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/orders/data/order_repository.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';

final orderRepositoryProvider = Provider<OrderRepository>(
  (ref) => OrderRepository(ref.watch(dioProvider)),
);

final orderDetailProvider = FutureProvider.autoDispose
    .family<OrderDetail, String>(
      (ref, orderId) => ref.watch(orderRepositoryProvider).get(orderId),
    );
