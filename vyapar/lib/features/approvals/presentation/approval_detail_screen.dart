import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/app_sheet.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/approvals/data/approval_repository.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class ApprovalDetailScreen extends ConsumerWidget {
  const ApprovalDetailScreen({required this.approvalId, super.key});

  final String approvalId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final approval = ref.watch(approvalControllerProvider(approvalId));
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Purchase approval',
                  subtitle: approvalId,
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: approval.when(
                  loading: () => const LoadingSkeleton(rows: 6),
                  error: (error, _) => AppErrorState(
                    error: error,
                    onRetry: () =>
                        ref.invalidate(approvalControllerProvider(approvalId)),
                  ),
                  data: (value) => _ApprovalBody(approval: value),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ApprovalBody extends ConsumerWidget {
  const _ApprovalBody({required this.approval});

  final ApprovalDetail approval;

  Future<void> _decide(
    BuildContext context,
    WidgetRef ref,
    ApprovalAction action,
  ) async {
    double? quantity;
    double? maxUnitPrice;
    if (action == ApprovalAction.modify) {
      final modification = await showAppSheet<_ProposalModification>(
        context: context,
        child: _ModifyProposalSheet(approval: approval),
      );
      if (modification == null || !context.mounted) return;
      quantity = modification.quantity;
      maxUnitPrice = modification.maxUnitPrice;
    }
    final label = switch (action) {
      ApprovalAction.approve => 'Approve exact proposal',
      ApprovalAction.modify => 'Modify proposal',
      ApprovalAction.reject => 'Reject proposal',
    };
    final confirmed = await showConfirmSheet(
      context: context,
      title: label,
      message: action == ApprovalAction.approve
          ? 'Only proposal ${approval.proposalId} with its verified hash will be approved.'
          : 'This updates only the current backend approval state.',
      confirmLabel: label,
    );
    if (!confirmed || !context.mounted) return;
    try {
      final result = await ref
          .read(approvalControllerProvider(approval.id).notifier)
          .decide(action, quantity: quantity, maxUnitPrice: maxUnitPrice);
      if (!context.mounted) return;
      if (result.orderId case final orderId?) {
        context.go('/order/$orderId');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result.status ?? 'Approval updated.')),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final actionContext = ref.watch(approvalContextsProvider)[approval.id];
    final tone = switch (approval.status) {
      'APPROVED' => StatusTone.success,
      'PENDING' => StatusTone.warning,
      'REJECTED' || 'EXPIRED' => StatusTone.danger,
      _ => StatusTone.neutral,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: AppSpacing.lg),
        StatusPill(label: sentenceCase(approval.status), tone: tone),
        const SizedBox(height: AppSpacing.lg),
        ProposalSummary(
          sku: approval.proposal.sku,
          quantity: approval.proposal.quantity,
          unit: approval.proposal.unit,
          unitPrice: approval.proposal.unitPrice,
          delivery: approval.proposal.deliveryAt,
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Expires ${formatDateTime(approval.expiresAt)}',
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
        ),
        const SizedBox(height: AppSpacing.xl),
        const Divider(),
        const SizedBox(height: AppSpacing.lg),
        Text('Verification', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: AppSpacing.md),
        AppTimeline(
          items: [
            const TimelineItem(title: 'Proposal created', complete: true),
            TimelineItem(
              title: 'Merchant decision',
              complete: approval.status != 'PENDING',
            ),
          ],
        ),
        if (approval.isPending) ...[
          if (actionContext == null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: Text(
                'Approval is read-only after a cold deep link because the backend does not return its short-lived approval token. Open it from the active Munim workflow to approve or modify.',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: AppColors.warning),
              ),
            ),
          PrimaryButton(
            key: const ValueKey('approve_button'),
            label: 'Approve',
            onPressed: actionContext == null
                ? null
                : () => _decide(context, ref, ApprovalAction.approve),
          ),
          const SizedBox(height: AppSpacing.xs),
          SecondaryButton(
            label: 'Modify',
            onPressed: actionContext?.requestId == null
                ? null
                : () => _decide(context, ref, ApprovalAction.modify),
          ),
          AppButton(
            label: 'Reject',
            style: AppButtonStyle.text,
            onPressed: () => _decide(context, ref, ApprovalAction.reject),
          ),
        ],
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }
}

class _ProposalModification {
  const _ProposalModification({this.quantity, this.maxUnitPrice});

  final double? quantity;
  final double? maxUnitPrice;
}

class _ModifyProposalSheet extends StatefulWidget {
  const _ModifyProposalSheet({required this.approval});

  final ApprovalDetail approval;

  @override
  State<_ModifyProposalSheet> createState() => _ModifyProposalSheetState();
}

class _ModifyProposalSheetState extends State<_ModifyProposalSheet> {
  late final TextEditingController _quantity;
  late final TextEditingController _price;

  @override
  void initState() {
    super.initState();
    _quantity = TextEditingController(
      text: widget.approval.proposal.quantity.toString(),
    );
    _price = TextEditingController(
      text: widget.approval.proposal.unitPrice.toString(),
    );
  }

  @override
  void dispose() {
    _quantity.dispose();
    _price.dispose();
    super.dispose();
  }

  void _submit() {
    final quantity = double.tryParse(_quantity.text.trim());
    final price = double.tryParse(_price.text.trim());
    if (quantity == null || quantity <= 0 || price == null || price <= 0) {
      return;
    }
    Navigator.of(
      context,
    ).pop(_ProposalModification(quantity: quantity, maxUnitPrice: price));
  }

  @override
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Modify exact proposal',
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      const SizedBox(height: AppSpacing.lg),
      TextField(
        controller: _quantity,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(
          labelText: 'Quantity (${widget.approval.proposal.unit})',
        ),
      ),
      const SizedBox(height: AppSpacing.md),
      TextField(
        controller: _price,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: const InputDecoration(labelText: 'Maximum unit price'),
      ),
      const SizedBox(height: AppSpacing.lg),
      PrimaryButton(label: 'Create revised proposal', onPressed: _submit),
    ],
  );
}
