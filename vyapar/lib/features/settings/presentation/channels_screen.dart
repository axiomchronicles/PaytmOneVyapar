import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';

class ChannelsScreen extends StatelessWidget {
  const ChannelsScreen({super.key});

  static const _telegramBotUsername = 'PaytmOneVyapar_bot';
  static const _telegramBotUrl = 'https://t.me/PaytmOneVyapar_bot';

  void _copyTelegramLink(BuildContext context) {
    Clipboard.setData(const ClipboardData(text: _telegramBotUrl));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Telegram bot link copied to clipboard!'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.all(AppSpacing.md),
            sliver: SliverToBoxAdapter(
              child: AppHeader(
                title: 'Communication channels',
                subtitle: 'Active and upcoming channels for merchant interactions',
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 1. Telegram Channel (ACTIVE)
                  _ChannelCard(
                    icon: VyaparIcons.telegram,
                    iconColor: const Color(0xFF229ED9),
                    title: 'Telegram Bot',
                    handle: '@$_telegramBotUsername',
                    tone: StatusTone.success,
                    statusLabel: 'ACTIVE',
                    description:
                        'Receive real-time stock alerts, AI replenishment recommendations, '
                        'and one-tap order approvals directly on Telegram. Fast, secure, and always on.',
                    features: const [
                      'One-tap purchase approvals (Approve, Modify, Decline)',
                      'Instant stock and replenishment alerts',
                      'Direct OTP code verification delivery',
                      'Merchant account linking via /connect',
                    ],
                    action: SecondaryButton(
                      label: 'Copy Bot Link',
                      onPressed: () => _copyTelegramLink(context),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.lg),

                  // 2. WhatsApp Business (COMING SOON)
                  const _ChannelCard(
                    icon: VyaparIcons.whatsapp,
                    iconColor: Color(0xFF25D366),
                    title: 'WhatsApp Business',
                    handle: 'Meta Cloud API',
                    tone: StatusTone.warning,
                    statusLabel: 'COMING SOON',
                    description:
                        'Meta WhatsApp Cloud API integration is currently in development. '
                        'Use the fully functional Telegram channel (@PaytmOneVyapar_bot) in the meantime.',
                    features: [
                      'Interactive message approval templates (In progress)',
                      'Business phone number mapping (In progress)',
                    ],
                  ),
                  const SizedBox(height: AppSpacing.lg),

                  // 3. Sarvam Voice Pipeline (ACTIVE)
                  const _ChannelCard(
                    icon: VyaparIcons.mic,
                    iconColor: AppColors.blue,
                    title: 'Sarvam Voice Assistant',
                    handle: 'saaras:v4 / bulbul:v3',
                    tone: StatusTone.success,
                    statusLabel: 'ACTIVE',
                    description:
                        'Real-time bilingual voice interface powered by Sarvam AI. '
                        'Speak in Hindi or English to check stock, review proposals, and approve orders.',
                    features: [
                      'Ultra-low latency speech-to-text and synthesis',
                      'Hindi, English, Hinglish language support',
                      'Voice approval and query parsing',
                    ],
                  ),
                  const SizedBox(height: AppSpacing.lg),

                  // 4. Transactional Email (ACTIVE)
                  const _ChannelCard(
                    icon: VyaparIcons.email,
                    iconColor: AppColors.navy,
                    title: 'Resend Email',
                    handle: 'auth@tuboxlabs.com',
                    tone: StatusTone.success,
                    statusLabel: 'ACTIVE',
                    description:
                        'Transactional email notifications for authentication, OTP security codes, and order confirmations.',
                    features: [
                      'Secure OTP codes for login and registration',
                      'Order execution receipts and invoices',
                    ],
                  ),
                  const SizedBox(height: AppSpacing.xxl),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _ChannelCard extends StatelessWidget {
  const _ChannelCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.handle,
    required this.tone,
    required this.statusLabel,
    required this.description,
    required this.features,
    this.action,
  });

  final List<List<dynamic>> icon;
  final Color iconColor;
  final String title;
  final String handle;
  final StatusTone tone;
  final String statusLabel;
  final String description;
  final List<String> features;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadii.lg),
      border: Border.all(color: AppColors.outline),
    ),
    padding: const EdgeInsets.all(AppSpacing.lg),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppRadii.md),
              ),
              child: Center(
                child: VyaparIcon(icon, color: iconColor, size: 24),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 2),
                  Text(
                    handle,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                  ),
                ],
              ),
            ),
            StatusPill(label: statusLabel, tone: tone),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          description,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: AppColors.text,
            height: 1.4,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        for (final feature in features) ...[
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xxs),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.only(top: 5),
                  child: Icon(Icons.circle, size: 5, color: AppColors.muted),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    feature,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: AppColors.muted),
                  ),
                ),
              ],
            ),
          ),
        ],
        if (action != null) ...[
          const SizedBox(height: AppSpacing.md),
          action!,
        ],
      ],
    ),
  );
}
