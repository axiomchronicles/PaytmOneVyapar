import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';

class CapabilitiesScreen extends StatelessWidget {
  const CapabilitiesScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.all(AppSpacing.md),
            sliver: SliverToBoxAdapter(
              child: AppHeader(
                title: 'Backend capabilities',
                subtitle: 'What this build can use safely today',
                leading: IconAction(
                  icon: VyaparIcons.back,
                  label: 'Back',
                  onPressed: context.pop,
                ),
              ),
            ),
          ),
          const SliverToBoxAdapter(
            child: AdaptivePadding(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Capability(
                    title: 'Connected',
                    body:
                        'Password and OTP auth, registration, OAuth exchange, merchant profile, inventory, approvals, orders, suppliers, negotiations, A2A activity, notifications, analytics, realtime events, and voice sessions.',
                    available: true,
                  ),
                  _Capability(
                    title: 'Interactive channels',
                    body:
                        'Telegram channel (@PaytmOneVyapar_bot) is active for real-time replenishment alerts, OTP security codes, and one-tap purchase approvals. WhatsApp channel is coming soon.',
                    available: true,
                  ),
                  _Capability(
                    title: 'External configuration',
                    body:
                        'Telegram bot channel is fully operational. WhatsApp Business channel is coming soon. Google and Apple require provider client IDs and platform setup. Sarvam requires a valid subscription key.',
                    available: true,
                  ),
                  _Capability(
                    title: 'Durable realtime',
                    body:
                        'Business changes commit with an outbox event before Redis fanout. Reconnects always refresh authoritative state.',
                    available: true,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _Capability extends StatelessWidget {
  const _Capability({
    required this.title,
    required this.body,
    required this.available,
  });

  final String title;
  final String body;
  final bool available;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        VyaparIcon(
          available ? VyaparIcons.success : VyaparIcons.warning,
          color: available ? AppColors.success : AppColors.warning,
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                body,
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}
