import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/features/procurement/data/procurement_repository.dart';
import 'package:vyapar/features/procurement/models/agent_run.dart';

final procurementRepositoryProvider = Provider<ProcurementRepository>(
  (ref) => ProcurementRepository(ref.watch(dioProvider)),
);

class ProcurementRun extends AsyncNotifier<AgentRunResult?> {
  @override
  Future<AgentRunResult?> build() async => null;

  Future<void> start(AgentRunRequest request) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final result = await ref
          .read(procurementRepositoryProvider)
          .start(request);
      final approvalId = result.approvalId;
      final token = result.approvalToken;
      if (approvalId != null && token != null) {
        ref
            .read(approvalContextsProvider.notifier)
            .register(
              approvalId,
              ApprovalActionContext(
                approvalToken: token,
                requestId: result.requestId,
              ),
            );
      }
      return result;
    });
  }
}

final procurementRunProvider =
    AsyncNotifierProvider.autoDispose<ProcurementRun, AgentRunResult?>(
      ProcurementRun.new,
    );
