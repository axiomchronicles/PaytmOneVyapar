import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/backgrounds/aurora_background.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/vyapar_logo.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/l10n/app_localizations.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: AuroraBackground(
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) => SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: constraints.maxHeight - 48,
                ),
                child: IntrinsicHeight(
                  child: Column(
                    children: [
                      const Align(
                        alignment: Alignment.centerLeft,
                        child: VyaparLogo(height: 40),
                      ),
                      const Spacer(),
                      const _WelcomeOrb(),
                      const SizedBox(height: AppSpacing.xl),
                      Text(
                        l10n.welcomeTitle,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.displaySmall,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        l10n.welcomeBody,
                        textAlign: TextAlign.center,
                        style: Theme.of(
                          context,
                        ).textTheme.bodyLarge?.copyWith(color: AppColors.muted),
                      ),
                      const Spacer(),
                      PrimaryButton(
                        key: const ValueKey('get_started_button'),
                        label: l10n.getStarted,
                        onPressed: () => context.go('/sign-in'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _WelcomeOrb extends StatelessWidget {
  const _WelcomeOrb();

  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Vyapar AI network',
    child: Container(
      width: 230,
      height: 230,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const RadialGradient(
          center: Alignment(0.25, 0.2),
          colors: [
            Colors.white,
            Color(0xFFBDEEFF),
            AppColors.cyan,
            AppColors.blue,
          ],
          stops: [0, 0.3, 0.68, 1],
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.cyan.withValues(alpha: 0.2),
            blurRadius: 38,
            spreadRadius: 12,
          ),
        ],
      ),
    ),
  );
}
