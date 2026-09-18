import 'package:flutter/material.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';

enum AppButtonStyle { primary, secondary, text }

class AppButton extends StatelessWidget {
  const AppButton({
    required this.label,
    required this.onPressed,
    super.key,
    this.style = AppButtonStyle.primary,
    this.loading = false,
    this.leading,
  });

  final String label;
  final VoidCallback? onPressed;
  final AppButtonStyle style;
  final bool loading;
  final Widget? leading;

  @override
  Widget build(BuildContext context) {
    final content = AnimatedSwitcher(
      duration: const Duration(milliseconds: 180),
      child: loading
          ? const SizedBox.square(
              key: ValueKey('button_loading'),
              dimension: 21,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Row(
              key: const ValueKey('button_content'),
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (leading case final icon?) ...[
                  icon,
                  const SizedBox(width: 10),
                ],
                Flexible(child: Text(label)),
              ],
            ),
    );
    final shape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppRadii.md),
    );
    final callback = loading ? null : onPressed;
    return switch (style) {
      AppButtonStyle.primary => SizedBox(
        width: double.infinity,
        height: 54,
        child: FilledButton(
          onPressed: callback,
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.navy,
            foregroundColor: Colors.white,
            shape: shape,
          ),
          child: content,
        ),
      ),
      AppButtonStyle.secondary => SizedBox(
        width: double.infinity,
        height: 54,
        child: OutlinedButton(
          onPressed: callback,
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.navy,
            side: const BorderSide(color: AppColors.navy),
            shape: shape,
          ),
          child: content,
        ),
      ),
      AppButtonStyle.text => TextButton(
        onPressed: callback,
        style: TextButton.styleFrom(foregroundColor: AppColors.navy),
        child: content,
      ),
    };
  }
}

class PrimaryButton extends AppButton {
  const PrimaryButton({
    required super.label,
    required super.onPressed,
    super.key,
    super.loading,
    super.leading,
  });
}

class SecondaryButton extends AppButton {
  const SecondaryButton({
    required super.label,
    required super.onPressed,
    super.key,
    super.loading,
    super.leading,
  }) : super(style: AppButtonStyle.secondary);
}
