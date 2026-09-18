import 'package:flutter/material.dart';
import 'package:vyapar/design_system/backgrounds/aurora_background.dart';
import 'package:vyapar/design_system/components/vyapar_logo.dart';
import 'package:vyapar/design_system/tokens/colors.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) => const Scaffold(
    body: AuroraBackground(
      child: SafeArea(
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              VyaparLogo(height: 52),
              SizedBox(height: 32),
              SizedBox.square(
                dimension: 24,
                child: CircularProgressIndicator(
                  color: AppColors.cyan,
                  strokeWidth: 2.4,
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
