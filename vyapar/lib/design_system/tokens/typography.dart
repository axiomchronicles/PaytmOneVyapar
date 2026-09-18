import 'package:flutter/material.dart';
import 'package:vyapar/design_system/tokens/colors.dart';

abstract final class AppTypography {
  static const textTheme = TextTheme(
    displaySmall: TextStyle(
      color: AppColors.text,
      fontSize: 38,
      height: 1.08,
      fontWeight: FontWeight.w700,
      letterSpacing: -1.2,
    ),
    headlineLarge: TextStyle(
      color: AppColors.text,
      fontSize: 30,
      height: 1.12,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.7,
    ),
    headlineMedium: TextStyle(
      color: AppColors.text,
      fontSize: 24,
      height: 1.2,
      fontWeight: FontWeight.w600,
      letterSpacing: -0.3,
    ),
    titleLarge: TextStyle(
      color: AppColors.text,
      fontSize: 20,
      height: 1.25,
      fontWeight: FontWeight.w600,
    ),
    titleMedium: TextStyle(
      color: AppColors.text,
      fontSize: 16,
      height: 1.35,
      fontWeight: FontWeight.w600,
    ),
    bodyLarge: TextStyle(
      color: AppColors.text,
      fontSize: 16,
      height: 1.5,
      fontWeight: FontWeight.w400,
    ),
    bodyMedium: TextStyle(
      color: AppColors.text,
      fontSize: 14,
      height: 1.45,
      fontWeight: FontWeight.w400,
    ),
    labelLarge: TextStyle(
      color: AppColors.text,
      fontSize: 15,
      height: 1.2,
      fontWeight: FontWeight.w600,
    ),
    labelMedium: TextStyle(
      color: AppColors.muted,
      fontSize: 12,
      height: 1.3,
      fontWeight: FontWeight.w600,
    ),
  );
}
