import 'package:flutter/material.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class AmountText extends StatelessWidget {
  const AmountText({required this.amount, super.key, this.label});

  final num amount;
  final String? label;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        formatInr(amount),
        style: Theme.of(context).textTheme.displaySmall?.copyWith(
          color: AppColors.navy,
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
      if (label case final value?)
        Text(value, style: Theme.of(context).textTheme.labelMedium),
    ],
  );
}

class AppChip extends StatelessWidget {
  const AppChip({
    required this.label,
    super.key,
    this.selected = false,
    this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => FilterChip(
    selected: selected,
    label: Text(label),
    onSelected: onTap == null ? null : (_) => onTap!(),
    backgroundColor: AppColors.surface,
    selectedColor: AppColors.paleBlue,
    side: const BorderSide(color: AppColors.outline),
  );
}

class ProposalSummary extends StatelessWidget {
  const ProposalSummary({
    required this.sku,
    required this.quantity,
    required this.unit,
    required this.unitPrice,
    required this.delivery,
    super.key,
  });

  final String sku;
  final double quantity;
  final String unit;
  final double unitPrice;
  final DateTime delivery;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      AmountText(amount: quantity * unitPrice, label: 'Purchase total'),
      const SizedBox(height: AppSpacing.lg),
      _SummaryLine(label: 'Product', value: sku),
      _SummaryLine(
        label: 'Quantity',
        value: '${formatQuantity(quantity)} $unit',
      ),
      _SummaryLine(
        label: 'Unit price',
        value: formatInr(unitPrice, decimals: true),
      ),
      _SummaryLine(label: 'Delivery', value: formatDateTime(delivery)),
    ],
  );
}

class _SummaryLine extends StatelessWidget {
  const _SummaryLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
      ],
    ),
  );
}

class SectionHeader extends StatelessWidget {
  const SectionHeader({required this.title, super.key, this.action});

  final String title;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: Text(title, style: Theme.of(context).textTheme.titleLarge),
      ),
      if (action case final widget?) widget,
    ],
  );
}

class MetricTile extends StatelessWidget {
  const MetricTile({
    required this.value,
    required this.label,
    super.key,
    this.accent = AppColors.navy,
  });

  final String value;
  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: accent.withValues(alpha: 0.07),
      borderRadius: BorderRadius.circular(AppRadii.md),
    ),
    child: Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            maxLines: 1,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              color: accent,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          const SizedBox(height: AppSpacing.xxs),
          Text(label, style: Theme.of(context).textTheme.labelMedium),
        ],
      ),
    ),
  );
}

class StatusPill extends StatelessWidget {
  const StatusPill({
    required this.label,
    super.key,
    this.tone = StatusTone.neutral,
  });

  final String label;
  final StatusTone tone;

  @override
  Widget build(BuildContext context) {
    final (foreground, background) = switch (tone) {
      StatusTone.success => (AppColors.success, AppColors.successSurface),
      StatusTone.warning => (AppColors.warning, AppColors.warningSurface),
      StatusTone.danger => (AppColors.danger, AppColors.dangerSurface),
      StatusTone.info => (AppColors.blue, AppColors.paleBlue),
      StatusTone.neutral => (AppColors.muted, AppColors.background),
    };
    return Semantics(
      label: 'Status: $label',
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(AppRadii.pill),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: foreground),
          ),
        ),
      ),
    );
  }
}

enum StatusTone { neutral, info, success, warning, danger }

class TimelineItem {
  const TimelineItem({
    required this.title,
    this.subtitle,
    this.complete = false,
  });

  final String title;
  final String? subtitle;
  final bool complete;
}

class AppTimeline extends StatelessWidget {
  const AppTimeline({required this.items, super.key});

  final List<TimelineItem> items;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (var index = 0; index < items.length; index++)
        _TimelineRow(item: items[index], last: index == items.length - 1),
    ],
  );
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.item, required this.last});

  final TimelineItem item;
  final bool last;

  @override
  Widget build(BuildContext context) => IntrinsicHeight(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 28,
          child: Column(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: item.complete ? AppColors.success : AppColors.outline,
                ),
              ),
              if (!last)
                Expanded(child: Container(width: 1, color: AppColors.outline)),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                if (item.subtitle case final subtitle?)
                  Text(
                    subtitle,
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
                  ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
}

class AgentStatusIndicator extends StatelessWidget {
  const AgentStatusIndicator({
    required this.label,
    super.key,
    this.active = false,
  });

  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      AnimatedContainer(
        duration: const Duration(milliseconds: 190),
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          color: active ? AppColors.success : AppColors.muted,
          shape: BoxShape.circle,
        ),
      ),
      const SizedBox(width: 7),
      Text(label, style: Theme.of(context).textTheme.labelMedium),
    ],
  );
}

class VoiceOrb extends StatelessWidget {
  const VoiceOrb({required this.active, super.key});

  final bool active;

  @override
  Widget build(BuildContext context) => AnimatedContainer(
    duration: const Duration(milliseconds: 260),
    width: active ? 132 : 116,
    height: active ? 132 : 116,
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      gradient: const RadialGradient(
        colors: [Color(0xFFDDF8FF), AppColors.cyan, AppColors.blue],
      ),
      boxShadow: [
        BoxShadow(
          color: AppColors.cyan.withValues(alpha: active ? 0.28 : 0.14),
          blurRadius: active ? 32 : 18,
          spreadRadius: active ? 8 : 2,
        ),
      ],
    ),
    child: Center(
      child: VyaparIcon(VyaparIcons.mic, size: 42, color: Colors.white),
    ),
  );
}

class VoiceTranscript extends StatelessWidget {
  const VoiceTranscript({required this.text, super.key, this.partial = false});

  final String text;
  final bool partial;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Text(
      text,
      textAlign: TextAlign.center,
      style: Theme.of(context).textTheme.titleLarge?.copyWith(
        color: partial ? AppColors.muted : AppColors.text,
        fontWeight: partial ? FontWeight.w400 : FontWeight.w600,
      ),
    ),
  );
}
