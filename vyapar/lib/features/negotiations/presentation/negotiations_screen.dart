import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/app_sheet.dart';
import 'package:vyapar/design_system/components/app_text_field.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/negotiations/models/negotiation.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class NegotiationsScreen extends ConsumerWidget {
  const NegotiationsScreen({super.key});

  void _openStartNegotiation(BuildContext context) {
    showAppSheet<void>(
      context: context,
      child: const _StartNegotiationSheet(),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final negotiations = ref.watch(negotiationListProvider);
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: ref.read(negotiationListProvider.notifier).refresh,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: AppHeader(
                    title: 'Negotiations',
                    subtitle: 'Autonomous supplier quotes and counter offers',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                    trailing: IconAction(
                      icon: VyaparIcons.add,
                      label: 'New',
                      onPressed: () => _openStartNegotiation(context),
                    ),
                  ),
                ),
              ),
              negotiations.when(
                loading: () =>
                    const SliverSection(child: ListSkeleton(rows: 6)),
                error: (error, _) => SliverFillRemaining(
                  hasScrollBody: false,
                  child: AppErrorState(error: error),
                ),
                data: (page) => page.items.isEmpty
                    ? SliverFillRemaining(
                        hasScrollBody: false,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const EmptyState(
                              title: 'No negotiations yet',
                              message:
                                  'Supplier conversations will appear after procurement starts.',
                            ),
                            const SizedBox(height: AppSpacing.md),
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: AppSpacing.xl,
                              ),
                              child: PrimaryButton(
                                label: 'Start New Negotiation',
                                leading: const VyaparIcon(
                                  VyaparIcons.add,
                                  color: Colors.white,
                                  size: 18,
                                ),
                                onPressed: () => _openStartNegotiation(context),
                              ),
                            ),
                          ],
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: page.items.length + (page.hasMore ? 1 : 0),
                          separatorBuilder: (_, _) =>
                              const SizedBox(height: AppSpacing.sm),
                          itemBuilder: (context, index) {
                            if (index == page.items.length) {
                              ref
                                  .read(negotiationListProvider.notifier)
                                  .loadMore();
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            }
                            final item = page.items[index];
                            return _NegotiationCard(
                              key: ValueKey('negotiation_${item.id}'),
                              item: item,
                            );
                          },
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.navy,
        foregroundColor: Colors.white,
        icon: const VyaparIcon(VyaparIcons.add, color: Colors.white, size: 20),
        label: const Text('Start Negotiation'),
        onPressed: () => _openStartNegotiation(context),
      ),
    );
  }
}

class _NegotiationCard extends StatelessWidget {
  const _NegotiationCard({required this.item, super.key});

  final NegotiationDetail item;

  StatusTone _statusTone(String status) => switch (status.toUpperCase()) {
    'ACCEPTED' => StatusTone.success,
    'COUNTER_OFFER' || 'IN_PROGRESS' || 'SUBMITTED' => StatusTone.warning,
    'REJECTED' || 'FAILED' => StatusTone.danger,
    _ => StatusTone.info,
  };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final initial = item.initialQuotePrice;
    final fin = item.finalPrice;
    final savings = item.savingsPerUnit;
    final pct = item.savingsPercent;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: AppColors.outline),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadii.md),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadii.md),
          onTap: () => context.push('/negotiations/${item.id}'),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: AppColors.paleBlue,
                        borderRadius: BorderRadius.circular(AppRadii.sm),
                      ),
                      child: const VyaparIcon(
                        VyaparIcons.truck,
                        size: 16,
                        color: AppColors.navy,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.xs),
                    Expanded(
                      child: Text(
                        item.supplierName,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.xs),
                    StatusPill(
                      label: sentenceCase(item.status),
                      tone: _statusTone(item.status),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  item.sku,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (item.quantity != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    '${item.quantity} units requested',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: AppColors.muted,
                    ),
                  ),
                ],
                const SizedBox(height: AppSpacing.sm),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    if (fin != null) ...[
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (initial != null && initial > fin)
                            Text(
                              'Initial: ${formatInr(initial, decimals: true)}',
                              style: theme.textTheme.labelSmall?.copyWith(
                                decoration: TextDecoration.lineThrough,
                                color: AppColors.muted,
                              ),
                            ),
                          Text(
                            '${formatInr(fin, decimals: true)}/unit',
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: AppColors.navy,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ],
                    if (savings != null && pct != null) ...[
                      const SizedBox(width: AppSpacing.sm),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.successSurface,
                          borderRadius: BorderRadius.circular(AppRadii.pill),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const VyaparIcon(
                              VyaparIcons.tag,
                              size: 12,
                              color: AppColors.success,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              'Saved ${formatInr(savings, decimals: true)} (${pct.toStringAsFixed(1)}%)',
                              style: theme.textTheme.labelSmall?.copyWith(
                                color: AppColors.success,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const Spacer(),
                    const VyaparIcon(
                      VyaparIcons.forward,
                      size: 18,
                      color: AppColors.muted,
                    ),
                  ],
                ),
                const Divider(height: AppSpacing.lg),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.background,
                        borderRadius: BorderRadius.circular(AppRadii.pill),
                        border: Border.all(color: AppColors.outline),
                      ),
                      child: Text(
                        '${item.roundCount} ${item.roundCount == 1 ? 'round' : 'rounds'}',
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: AppColors.muted,
                        ),
                      ),
                    ),
                    const Spacer(),
                    Text(
                      formatDateTime(item.createdAt),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: AppColors.muted,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StartNegotiationSheet extends ConsumerStatefulWidget {
  const _StartNegotiationSheet();

  @override
  ConsumerState<_StartNegotiationSheet> createState() =>
      _StartNegotiationSheetState();
}

class _StartNegotiationSheetState
    extends ConsumerState<_StartNegotiationSheet> {
  final _formKey = GlobalKey<FormState>();
  final _skuController = TextEditingController(text: 'COLD-COLA-300');
  final _quantityController = TextEditingController(text: '50');
  final _targetPriceController = TextEditingController(text: '435');
  final _maxPriceController = TextEditingController(text: '460');
  bool _loading = false;
  String? _errorMessage;

  static const _quickPresets = [
    (sku: 'COLD-COLA-300', label: 'Cola 300ml', target: '435', max: '460'),
    (sku: 'TATA-SALT-1KG', label: 'Tata Salt 1kg', target: '23', max: '25'),
    (sku: 'FORTUNE-OIL-1L', label: 'Fortune Oil 1L', target: '135', max: '145'),
    (sku: 'MAGGI-70G', label: 'Maggi 70g', target: '12', max: '14'),
    (sku: 'AASHIRVAAD-ATTA-5KG', label: 'Atta 5kg', target: '215', max: '235'),
  ];

  @override
  void dispose() {
    _skuController.dispose();
    _quantityController.dispose();
    _targetPriceController.dispose();
    _maxPriceController.dispose();
    super.dispose();
  }

  void _applyPreset(
    String sku,
    String target,
    String max,
  ) {
    setState(() {
      _skuController.text = sku;
      _targetPriceController.text = target;
      _maxPriceController.text = max;
    });
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    try {
      final sku = _skuController.text.trim();
      final quantity = num.tryParse(_quantityController.text.trim());
      final targetPrice = num.tryParse(_targetPriceController.text.trim());
      final maxPrice = num.tryParse(_maxPriceController.text.trim());

      final result = await ref
          .read(negotiationListProvider.notifier)
          .startNegotiation(
            sku: sku,
            quantity: quantity,
            targetPrice: targetPrice,
            maxPrice: maxPrice,
          );

      if (mounted) {
        Navigator.of(context).pop();
        context.push('/negotiations/${result.id}');
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _errorMessage = e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Form(
      key: _formKey,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.paleBlue,
                    borderRadius: BorderRadius.circular(AppRadii.sm),
                  ),
                  child: const VyaparIcon(
                    VyaparIcons.munim,
                    size: 20,
                    color: AppColors.navy,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Start Agent Negotiation',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'Autonomous A2A protocol negotiation with B2B suppliers',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: AppColors.muted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Quick FMCG Presets',
              style: theme.textTheme.labelMedium?.copyWith(
                color: AppColors.muted,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final p in _quickPresets)
                  ActionChip(
                    label: Text(p.label),
                    backgroundColor: _skuController.text == p.sku
                        ? AppColors.paleBlue
                        : AppColors.surface,
                    side: BorderSide(
                      color: _skuController.text == p.sku
                          ? AppColors.blue
                          : AppColors.outline,
                    ),
                    onPressed: () => _applyPreset(p.sku, p.target, p.max),
                  ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _skuController,
              label: 'SKU Identifier',
              hint: 'e.g. COLD-COLA-300',
              prefixIcon: VyaparIcons.tag,
              validator: (v) =>
                  v == null || v.trim().isEmpty ? 'SKU is required' : null,
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                Expanded(
                  child: AppTextField(
                    controller: _quantityController,
                    label: 'Quantity (units)',
                    hint: '50',
                    keyboardType: TextInputType.number,
                    prefixIcon: VyaparIcons.inventory,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: AppTextField(
                    controller: _targetPriceController,
                    label: 'Target (₹)',
                    hint: '435',
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    prefixIcon: VyaparIcons.coins,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            AppTextField(
              controller: _maxPriceController,
              label: 'Max Price Ceiling (₹)',
              hint: '460',
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              prefixIcon: VyaparIcons.moneyReceive,
            ),
            const SizedBox(height: AppSpacing.sm),
            Container(
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.circular(AppRadii.sm),
                border: Border.all(color: AppColors.outline),
              ),
              child: Row(
                children: [
                  const VyaparIcon(
                    VyaparIcons.security,
                    size: 16,
                    color: AppColors.blue,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Signed with HMAC-SHA256 over vyapaar-a2a-v1 with replay protection.',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: AppColors.muted,
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                _errorMessage!,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: AppColors.danger,
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.lg),
            PrimaryButton(
              label: 'Launch Agent Negotiation',
              loading: _loading,
              leading: const VyaparIcon(
                VyaparIcons.munim,
                color: Colors.white,
                size: 18,
              ),
              onPressed: _loading ? null : _submit,
            ),
            const SizedBox(height: AppSpacing.xs),
          ],
        ),
      ),
    );
  }
}
