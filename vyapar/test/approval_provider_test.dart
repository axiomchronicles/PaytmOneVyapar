import 'package:decimal/decimal.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/features/approvals/data/approval_repository.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';

class _FakeApprovalRepository extends ApprovalRepository {
  _FakeApprovalRepository(this.detail) : super(Dio());

  ApprovalDetail detail;
  ApprovalAction? lastAction;
  ApprovalActionContext? lastContext;
  Decimal? lastQuantity;

  @override
  Future<ApprovalDetail> get(String approvalId) async => detail;

  @override
  Future<ApprovalActionResult> decide({
    required String approvalId,
    required ApprovalAction action,
    ApprovalActionContext? context,
    Decimal? quantity,
    Decimal? maxUnitPrice,
  }) async {
    lastAction = action;
    lastContext = context;
    lastQuantity = quantity;
    detail = ApprovalDetail(
      id: detail.id,
      proposalId: detail.proposalId,
      orderHash: detail.orderHash,
      proposal: detail.proposal,
      status: action == ApprovalAction.reject ? 'REJECTED' : 'APPROVED',
      expiresAt: detail.expiresAt,
      createdAt: detail.createdAt,
    );
    return ApprovalActionResult(
      approvalId: approvalId,
      orderId: action == ApprovalAction.approve ? 'order-id' : null,
      status: detail.status,
    );
  }
}

final proposal = ProposalDetail(
  proposalId: 'proposal-id',
  storeId: 'store-id',
  supplierId: 'supplier-id',
  sku: 'COLD-COLA-300',
  quantity: Decimal.fromInt(5),
  unit: 'crate',
  unitPrice: Decimal.fromInt(470),
  currency: 'INR',
  deliveryAt: DateTime(2026, 9, 20),
  quoteId: 'quote-id',
);

ApprovalDetail pendingApproval() => ApprovalDetail(
  id: 'approval-id',
  proposalId: proposal.proposalId,
  orderHash: List<String>.filled(64, 'a').join(),
  proposal: proposal,
  status: 'PENDING',
  expiresAt: DateTime(2026, 9, 19),
  createdAt: DateTime(2026, 9, 18),
);

void main() {
  test(
    'approve forwards the exact workflow token and returns order ID',
    () async {
      final repository = _FakeApprovalRepository(pendingApproval());
      final container = ProviderContainer(
        overrides: [approvalRepositoryProvider.overrideWithValue(repository)],
      );
      addTearDown(container.dispose);
      container
          .read(approvalContextsProvider.notifier)
          .register(
            'approval-id',
            const ApprovalActionContext(
              approvalToken: 'signed-exact-proposal-token',
              requestId: 'request-id',
            ),
          );
      await container.read(approvalControllerProvider('approval-id').future);

      final result = await container
          .read(approvalControllerProvider('approval-id').notifier)
          .decide(ApprovalAction.approve);

      expect(repository.lastAction, ApprovalAction.approve);
      expect(
        repository.lastContext?.approvalToken,
        'signed-exact-proposal-token',
      );
      expect(result.orderId, 'order-id');
    },
  );

  test('modify forwards the merchant quantity for a new revision', () async {
    final repository = _FakeApprovalRepository(pendingApproval());
    final container = ProviderContainer(
      overrides: [approvalRepositoryProvider.overrideWithValue(repository)],
    );
    addTearDown(container.dispose);
    container
        .read(approvalContextsProvider.notifier)
        .register(
          'approval-id',
          const ApprovalActionContext(
            approvalToken: 'signed-exact-proposal-token',
            requestId: 'request-id',
          ),
        );
    await container.read(approvalControllerProvider('approval-id').future);

    await container
        .read(approvalControllerProvider('approval-id').notifier)
        .decide(ApprovalAction.modify, quantity: Decimal.fromInt(2));

    expect(repository.lastAction, ApprovalAction.modify);
    expect(repository.lastQuantity, Decimal.fromInt(2));
  });

  test('reject remains available for a pending deep-linked approval', () async {
    final repository = _FakeApprovalRepository(pendingApproval());
    final container = ProviderContainer(
      overrides: [approvalRepositoryProvider.overrideWithValue(repository)],
    );
    addTearDown(container.dispose);
    await container.read(approvalControllerProvider('approval-id').future);

    await container
        .read(approvalControllerProvider('approval-id').notifier)
        .decide(ApprovalAction.reject);

    expect(repository.lastAction, ApprovalAction.reject);
    expect(repository.lastContext, isNull);
    expect(
      container
          .read(approvalControllerProvider('approval-id'))
          .requireValue
          .status,
      'REJECTED',
    );
  });

  test('expired approval state is preserved from the backend', () async {
    final stale = pendingApproval();
    final repository = _FakeApprovalRepository(
      ApprovalDetail(
        id: stale.id,
        proposalId: stale.proposalId,
        orderHash: stale.orderHash,
        proposal: stale.proposal,
        status: 'EXPIRED',
        expiresAt: stale.expiresAt,
        createdAt: stale.createdAt,
      ),
    );
    final container = ProviderContainer(
      overrides: [approvalRepositoryProvider.overrideWithValue(repository)],
    );
    addTearDown(container.dispose);

    final approval = await container.read(
      approvalControllerProvider('approval-id').future,
    );
    expect(approval.status, 'EXPIRED');
    expect(approval.isPending, isFalse);
  });
}
