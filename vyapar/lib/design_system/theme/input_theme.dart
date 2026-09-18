import 'package:flutter/material.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';

InputDecorationTheme buildInputTheme() {
  final border = OutlineInputBorder(
    borderRadius: BorderRadius.circular(AppRadii.md),
    borderSide: const BorderSide(color: AppColors.outline),
  );
  return InputDecorationTheme(
    filled: true,
    fillColor: AppColors.surface,
    contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 17),
    border: border,
    enabledBorder: border,
    focusedBorder: border.copyWith(
      borderSide: const BorderSide(color: AppColors.cyan, width: 1.5),
    ),
    errorBorder: border.copyWith(
      borderSide: const BorderSide(color: AppColors.danger),
    ),
    focusedErrorBorder: border.copyWith(
      borderSide: const BorderSide(color: AppColors.danger, width: 1.5),
    ),
    hintStyle: const TextStyle(color: AppColors.muted),
  );
}
