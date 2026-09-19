import 'package:decimal/decimal.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/features/approvals/data/approval_repository.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/orders/providers/order_provider.dart';

final approvalRepositoryProvider = Provider<ApprovalRepository>(
  (ref) => ApprovalRepository(ref.watch(dioProvider)),
);

class ApprovalContexts extends Notifier<Map<String, ApprovalActionContext>> {
  @override
  Map<String, ApprovalActionContext> build() => const {};

  void register(String approvalId, ApprovalActionContext context) {
    state = {...state, approvalId: context};
  }

  void remove(String approvalId) {
    state = Map<String, ApprovalActionContext>.of(state)..remove(approvalId);
  }
}

final approvalContextsProvider =
    NotifierProvider<ApprovalContexts, Map<String, ApprovalActionContext>>(
      ApprovalContexts.new,
    );

class ApprovalListController extends AsyncNotifier<CursorPage<ApprovalDetail>> {
  @override
  Future<CursorPage<ApprovalDetail>> build() =>
      ref.watch(approvalRepositoryProvider).list();

  Future<void> refresh() async {
    state = await AsyncValue.guard(
      () => ref.read(approvalRepositoryProvider).list(),
    );
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (state.isLoading || current?.nextCursor == null) return;
    final next = await ref
        .read(approvalRepositoryProvider)
        .list(cursor: current!.nextCursor);
    state = AsyncData(current.append(next, (item) => item.id));
  }
}

final approvalListProvider =
    AsyncNotifierProvider<ApprovalListController, CursorPage<ApprovalDetail>>(
      ApprovalListController.new,
    );

class ApprovalController extends AsyncNotifier<ApprovalDetail> {
  ApprovalController(this._approvalId);

  final String _approvalId;

  @override
  Future<ApprovalDetail> build() =>
      ref.watch(approvalRepositoryProvider).get(_approvalId).then((detail) {
        if (detail.actionToken case final token?) {
          ref
              .read(approvalContextsProvider.notifier)
              .register(
                detail.id,
                ApprovalActionContext(
                  approvalToken: token,
                  requestId: detail.workflowRequestId,
                ),
              );
        }
        return detail;
      });

  Future<ApprovalActionResult> decide(
    ApprovalAction action, {
    Decimal? quantity,
    Decimal? maxUnitPrice,
  }) async {
    state = const AsyncLoading();
    try {
      final context = ref.read(approvalContextsProvider)[_approvalId];
      final result = await ref
          .read(approvalRepositoryProvider)
          .decide(
            approvalId: _approvalId,
            action: action,
            context: context,
            quantity: quantity,
            maxUnitPrice: maxUnitPrice,
          );
      if (result.approvalId case final nextId?) {
        if (nextId != _approvalId && context != null) {
          ref.read(approvalContextsProvider.notifier).register(nextId, context);
        }
      }
      state = AsyncData(
        await ref.read(approvalRepositoryProvider).get(_approvalId),
      );
      ref.invalidate(approvalListProvider);
      // An approved proposal creates an order synchronously (or hands it to
      // the supplier approval stage). Refresh the persistent Orders tab now.
      ref.invalidate(orderListProvider);
      if (result.orderId case final orderId?) {
        ref.invalidate(orderDetailProvider(orderId));
      }
      return result;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }
}

final approvalControllerProvider = AsyncNotifierProvider.autoDispose
    .family<ApprovalController, ApprovalDetail, String>(ApprovalController.new);
