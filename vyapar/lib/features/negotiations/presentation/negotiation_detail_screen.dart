import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class NegotiationDetailScreen extends ConsumerWidget {
  const NegotiationDetailScreen({required this.negotiationId, super.key});

  final String negotiationId;

  StatusTone _statusTone(String status) => switch (status.toUpperCase()) {
    'ACCEPTED' => StatusTone.success,
    'COUNTER_OFFER' || 'IN_PROGRESS' || 'SUBMITTED' => StatusTone.warning,
    'REJECTED' || 'FAILED' => StatusTone.danger,
    _ => StatusTone.info,
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(negotiationDetailProvider(negotiationId));
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Negotiation detail',
                  subtitle: negotiationId,
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
                child: value.when(
                  loading: () => const NegotiationDetailSkeleton(),
                  error: (error, _) => AppErrorState(error: error),
                  data: (item) => Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header Card
                      Container(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(AppRadii.md),
                          border: Border.all(color: AppColors.outline),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: AppColors.paleBlue,
                                    borderRadius: BorderRadius.circular(
                                      AppRadii.sm,
                                    ),
                                  ),
                                  child: const VyaparIcon(
                                    VyaparIcons.truck,
                                    size: 20,
                                    color: AppColors.navy,
                                  ),
                                ),
                                const SizedBox(width: AppSpacing.sm),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        item.supplierName,
                                        style: theme.textTheme.headlineSmall
                                            ?.copyWith(
                                              fontWeight: FontWeight.bold,
                                            ),
                                      ),
                                      Row(
                                        children: [
                                          const VyaparIcon(
                                            VyaparIcons.security,
                                            size: 14,
                                            color: AppColors.blue,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            'Verified B2B Supplier',
                                            style: theme.textTheme.bodySmall
                                                ?.copyWith(
                                                  color: AppColors.blue,
                                                  fontWeight: FontWeight.w500,
                                                ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                StatusPill(
                                  label: sentenceCase(item.status),
                                  tone: _statusTone(item.status),
                                ),
                              ],
                            ),
                            const Divider(height: AppSpacing.lg),
                            Text(
                              item.sku,
                              style: theme.textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            if (item.quantity != null) ...[
                              const SizedBox(height: 2),
                              Text(
                                '${item.quantity} units requested',
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: AppColors.muted,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.md),

                      // Metrics
                      Row(
                        children: [
                          Expanded(
                            child: MetricTile(
                              label: 'Agreed Price',
                              value: item.finalPrice != null
                                  ? formatInr(item.finalPrice!, decimals: true)
                                  : 'Pending',
                              accent: AppColors.navy,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: MetricTile(
                              label: 'Initial Quote',
                              value: item.initialQuotePrice != null
                                  ? formatInr(
                                      item.initialQuotePrice!,
                                      decimals: true,
                                    )
                                  : 'None',
                              accent: AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Row(
                        children: [
                          Expanded(
                            child: MetricTile(
                              label: 'Target Limit',
                              value: item.targetPrice != null
                                  ? formatInr(item.targetPrice!, decimals: true)
                                  : 'None',
                              accent: AppColors.blue,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: MetricTile(
                              label: 'Unit Savings',
                              value: item.savingsPerUnit != null
                                  ? '${formatInr(item.savingsPerUnit!, decimals: true)} (${item.savingsPercent?.toStringAsFixed(1)}%)'
                                  : 'None',
                              accent: item.savingsPerUnit != null
                                  ? AppColors.success
                                  : AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.lg),

                      // Proposal Link Action
                      if (item.approvalId != null) ...[
                        Container(
                          padding: const EdgeInsets.all(AppSpacing.md),
                          decoration: BoxDecoration(
                            color: AppColors.paleBlue,
                            borderRadius: BorderRadius.circular(AppRadii.md),
                            border: Border.all(
                              color: AppColors.blue.withValues(alpha: 0.2),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const VyaparIcon(
                                    VyaparIcons.orders,
                                    size: 18,
                                    color: AppColors.navy,
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Purchase Proposal Ready',
                                    style: theme.textTheme.titleMedium
                                        ?.copyWith(fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Agent completed negotiation and staged an executable purchase proposal.',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: AppColors.muted,
                                ),
                              ),
                              const SizedBox(height: AppSpacing.md),
                              PrimaryButton(
                                label: 'Review & Approve Proposal',
                                onPressed: () => context.push(
                                  '/approval/${item.approvalId}',
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppSpacing.lg),
                      ],

                      // Round by round timeline
                      const SectionHeader(title: 'Negotiation Rounds'),
                      const SizedBox(height: AppSpacing.md),
                      if (item.history.isEmpty)
                        Text(
                          'No history events recorded yet.',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: AppColors.muted,
                          ),
                        )
                      else
                        AppTimeline(
                          items: [
                            for (final event in item.history)
                              TimelineItem(
                                title: _eventTitle(event),
                                subtitle: _eventSubtitle(event),
                                complete: true,
                              ),
                          ],
                        ),

                      const SizedBox(height: AppSpacing.lg),

                      // Cryptographic A2A Trail
                      Container(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: AppColors.background,
                          borderRadius: BorderRadius.circular(AppRadii.md),
                          border: Border.all(color: AppColors.outline),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const VyaparIcon(
                                  VyaparIcons.security,
                                  size: 18,
                                  color: AppColors.blue,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  'vyapaar-a2a-v1 Cryptographic Audit',
                                  style: theme.textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Protocol: vyapaar-a2a-v1 · Envelope HMAC-SHA256 Signed · Nonce Replay Protected',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: AppColors.muted,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Correlation ID: ${item.correlationId}',
                              style: theme.textTheme.labelSmall?.copyWith(
                                color: AppColors.muted,
                                fontFamily: 'monospace',
                              ),
                            ),
                            const SizedBox(height: AppSpacing.md),
                            SecondaryButton(
                              label: 'Inspect A2A Protocol Messages',
                              leading: const VyaparIcon(
                                VyaparIcons.security,
                                size: 18,
                              ),
                              onPressed: () => context.push(
                                '/a2a-activity/${item.correlationId}',
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xl),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _eventTitle(JsonMap event) {
    final round = event['round'];
    final eventName = event['event']?.toString().toUpperCase();
    final status = event['status']?.toString().toUpperCase();

    final roundPrefix = round != null ? 'Round $round · ' : '';
    if (eventName == 'BUYER_RFQ') {
      return '${roundPrefix}Buyer Quote Request';
    } else if (eventName == 'INITIAL_QUOTE') {
      return '${roundPrefix}Supplier Initial Quote';
    } else if (eventName == 'COUNTER_OFFER') {
      return '${roundPrefix}Agent Counter Offer';
    } else if (eventName == 'ACCEPTED') {
      return '${roundPrefix}Supplier Accepted Quote';
    } else if (eventName == 'REJECTED') {
      return '${roundPrefix}Negotiation Rejected';
    }
    return '$roundPrefix${sentenceCase(status ?? eventName ?? 'Update')}';
  }

  String _eventSubtitle(JsonMap event) {
    final buffer = StringBuffer();
    final unitPrice = event['unit_price'];
    if (unitPrice != null) {
      final parsed = num.tryParse(unitPrice.toString());
      if (parsed != null) {
        buffer.write('Unit price ${formatInr(parsed, decimals: true)}');
      }
    }
    final quantity = event['quantity'];
    if (quantity != null) {
      if (buffer.isNotEmpty) buffer.write(' · ');
      buffer.write('$quantity units');
    }
    final notes = event['notes'];
    if (notes != null && notes.toString().isNotEmpty) {
      if (buffer.isNotEmpty) buffer.write('\n');
      buffer.write(notes.toString());
    }
    final timestamp = event['timestamp'] ?? event['created_at'];
    if (timestamp != null) {
      final dt = DateTime.tryParse(timestamp.toString());
      if (dt != null) {
        if (buffer.isNotEmpty) buffer.write(' · ');
        buffer.write(formatDateTime(dt));
      }
    }
    return buffer.toString();
  }
}
