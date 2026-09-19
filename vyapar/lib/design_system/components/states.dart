import 'package:flutter/material.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/shimmer.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';

export 'package:vyapar/design_system/components/shimmer.dart';

class EmptyState extends StatelessWidget {
  const EmptyState({
    required this.title,
    required this.message,
    super.key,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 380),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            VyaparIcon(VyaparIcons.inbox, size: 36, color: AppColors.muted),
            const SizedBox(height: AppSpacing.md),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
            ),
            if (actionLabel case final label?) ...[
              const SizedBox(height: AppSpacing.lg),
              AppButton(
                label: label,
                onPressed: onAction,
                style: AppButtonStyle.text,
              ),
            ],
          ],
        ),
      ),
    ),
  );
}

class AppErrorState extends StatelessWidget {
  const AppErrorState({required this.error, super.key, this.onRetry});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final failure = error is AppFailure ? error as AppFailure : null;
    final message = failure != null
        ? failure.message
        : 'The page could not be loaded.';
    return EmptyState(
      title: failure?.kind == FailureKind.validation
          ? 'Check the form'
          : 'Couldn’t load this',
      message: message,
      actionLabel: onRetry == null ? null : 'Try again',
      onAction: onRetry,
    );
  }
}

class LoadingSkeleton extends StatelessWidget {
  const LoadingSkeleton({super.key, this.rows = 4});

  final int rows;

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: Column(
      children: List<Widget>.generate(rows, (index) => const SkeletonTile()),
    ),
  );
}

class NetworkBanner extends StatelessWidget {
  const NetworkBanner({required this.visible, super.key});

  final bool visible;

  @override
  Widget build(BuildContext context) => AnimatedSize(
    duration: const Duration(milliseconds: 190),
    child: visible
        ? Semantics(
            liveRegion: true,
            child: Container(
              width: double.infinity,
              color: AppColors.warningSurface,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  VyaparIcon(
                    VyaparIcons.offline,
                    size: 17,
                    color: AppColors.warning,
                  ),
                  SizedBox(width: 8),
                  Flexible(
                    child: Text('Offline — showing the last loaded view'),
                  ),
                ],
              ),
            ),
          )
        : const SizedBox.shrink(),
  );
}

class PermissionPrompt extends StatelessWidget {
  const PermissionPrompt({required this.onRequest, super.key});

  final VoidCallback onRequest;

  @override
  Widget build(BuildContext context) => EmptyState(
    title: 'Microphone access needed',
    message:
        'Vyapar sends live microphone audio only to your authenticated voice session.',
    actionLabel: 'Allow microphone',
    onAction: onRequest,
  );
}
