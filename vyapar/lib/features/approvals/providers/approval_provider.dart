import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/approvals/data/approval_repository.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';

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

class ApprovalController extends AsyncNotifier<ApprovalDetail> {
  ApprovalController(this._approvalId);

  final String _approvalId;

  @override
  Future<ApprovalDetail> build() =>
      ref.watch(approvalRepositoryProvider).get(_approvalId);

  Future<ApprovalActionResult> decide(
    ApprovalAction action, {
    double? quantity,
    double? maxUnitPrice,
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
      return result;
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      rethrow;
    }
  }
}

final approvalControllerProvider = AsyncNotifierProvider.autoDispose
    .family<ApprovalController, ApprovalDetail, String>(ApprovalController.new);
