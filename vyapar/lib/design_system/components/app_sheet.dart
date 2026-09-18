import 'package:flutter/material.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';

Future<T?> showAppSheet<T>({
  required BuildContext context,
  required Widget child,
}) => showModalBottomSheet<T>(
  context: context,
  isScrollControlled: true,
  useSafeArea: true,
  builder: (context) => Padding(
    padding: EdgeInsets.fromLTRB(
      AppSpacing.lg,
      AppSpacing.sm,
      AppSpacing.lg,
      MediaQuery.viewInsetsOf(context).bottom + AppSpacing.lg,
    ),
    child: child,
  ),
);

Future<bool> showConfirmSheet({
  required BuildContext context,
  required String title,
  required String message,
  required String confirmLabel,
}) async =>
    await showAppSheet<bool>(
      context: context,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: AppSpacing.sm),
          Text(message),
          const SizedBox(height: AppSpacing.lg),
          PrimaryButton(
            label: confirmLabel,
            onPressed: () => Navigator.of(context).pop(true),
          ),
          const SizedBox(height: AppSpacing.xs),
          AppButton(
            label: 'Cancel',
            style: AppButtonStyle.text,
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    ) ??
    false;
