import 'package:flutter/material.dart';
import 'package:vyapar/design_system/backgrounds/organic_pattern.dart';
import 'package:vyapar/design_system/tokens/colors.dart';

class AuroraBackground extends StatelessWidget {
  const AuroraBackground({
    required this.child,
    super.key,
    this.decorative = true,
  });

  final Widget child;
  final bool decorative;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: const BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0xFFF0FAFF), AppColors.surface, AppColors.background],
        stops: [0, 0.48, 1],
      ),
    ),
    child: Stack(
      fit: StackFit.expand,
      children: [if (decorative) const OrganicPattern(intensity: 0.8), child],
    ),
  );
}
