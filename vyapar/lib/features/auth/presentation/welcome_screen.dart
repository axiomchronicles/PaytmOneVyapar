import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/vyapar_logo.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/l10n/app_localizations.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key, this.redirect});

  final String? redirect;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/splash_screen_bg.webp',
            fit: BoxFit.cover,
          ),
          SafeArea(
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
                          onPressed: () => context.go(
                            Uri(
                              path: '/sign-in',
                              queryParameters: redirect == null
                                  ? null
                                  : {'redirect': redirect!},
                            ).toString(),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
