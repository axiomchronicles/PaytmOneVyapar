import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/approvals/models/approval_detail.dart';
import 'package:vyapar/features/approvals/providers/approval_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class ApprovalsScreen extends ConsumerWidget {
  const ApprovalsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final approvals = ref.watch(approvalListProvider);
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: ref.read(approvalListProvider.notifier).refresh,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: 'Approvals',
                    subtitle: 'Exact proposals awaiting your decision',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
              approvals.when(
                loading: () =>
                    const SliverSection(child: ListSkeleton(rows: 6)),
                error: (error, _) => SliverFillRemaining(
                  hasScrollBody: false,
                  child: AppErrorState(
                    error: error,
                    onRetry: ref.read(approvalListProvider.notifier).refresh,
                  ),
                ),
                data: (page) => page.items.isEmpty
                    ? const SliverFillRemaining(
                        hasScrollBody: false,
                        child: EmptyState(
                          title: 'No approvals',
                          message: 'New purchase proposals will appear here.',
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: page.items.length + (page.hasMore ? 1 : 0),
                          separatorBuilder: (_, _) => const Divider(indent: 52),
                          itemBuilder: (context, index) {
                            if (index == page.items.length) {
                              ref
                                  .read(approvalListProvider.notifier)
                                  .loadMore();
                              return const Padding(
                                padding: EdgeInsets.all(AppSpacing.md),
                                child: Center(
                                  child: CircularProgressIndicator(),
                                ),
                              );
                            }
                            return _ApprovalRow(approval: page.items[index]);
                          },
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ApprovalRow extends StatelessWidget {
  const _ApprovalRow({required this.approval});

  final ApprovalDetail approval;

  @override
  Widget build(BuildContext context) => ListTile(
    key: ValueKey('approval_${approval.id}'),
    contentPadding: EdgeInsets.zero,
    minTileHeight: 72,
    leading: VyaparIcon(
      approval.isPending ? VyaparIcons.clock : VyaparIcons.success,
      color: approval.isPending ? AppColors.warning : AppColors.success,
    ),
    title: Text(approval.proposal.sku),
    subtitle: Text(
      '${formatQuantity(approval.proposal.quantity)} ${approval.proposal.unit} · revision ${approval.revision}',
    ),
    trailing: StatusPill(
      label: sentenceCase(approval.status),
      tone: approval.isPending ? StatusTone.warning : StatusTone.neutral,
    ),
    onTap: () => context.push('/approval/${approval.id}'),
  );
}
