import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class NegotiationDetailScreen extends ConsumerWidget {
  const NegotiationDetailScreen({required this.negotiationId, super.key});

  final String negotiationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(negotiationDetailProvider(negotiationId));
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
                      Text(
                        item.supplierName,
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      Text(item.sku),
                      const SizedBox(height: AppSpacing.md),
                      StatusPill(label: sentenceCase(item.status)),
                      const SizedBox(height: AppSpacing.xl),
                      AppTimeline(
                        items: [
                          for (final event in item.history)
                            TimelineItem(
                              title: sentenceCase(
                                jsonOptionalString(event['status']) ?? 'UPDATE',
                              ),
                              subtitle: _price(event),
                              complete: true,
                            ),
                        ],
                      ),
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

  String? _price(JsonMap event) {
    final value = event['unit_price'];
    return value == null
        ? null
        : 'Unit price ${formatInr(num.parse(value.toString()), decimals: true)}';
  }
}
