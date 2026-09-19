import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_text_field.dart';
import 'package:vyapar/design_system/components/vyapar_logo.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/l10n/app_localizations.dart';

class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key, this.redirect});

  final String? redirect;

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    TextInput.finishAutofillContext();
    await ref
        .read(authControllerProvider.notifier)
        .signIn(email: _email.text, password: _password.text);
  }

  Future<void> _oauth(String provider) async {
    try {
      final registration = await ref
          .read(oauthFlowProvider.notifier)
          .authenticate(provider);
      if (mounted && registration == true) context.go('/register');
    } on Object {
      // The provider error is rendered in this view.
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final auth = ref.watch(authControllerProvider);
    final oauth = ref.watch(oauthFlowProvider);
    final failure = auth.error;
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/backgound_screen_auth.webp',
            fit: BoxFit.cover,
          ),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, constraints) {
              final horizontal = constraints.maxWidth > 640
                  ? (constraints.maxWidth - 560) / 2
                  : AppSpacing.lg;
              return AutofillGroup(
                child: ListView(
                  padding: EdgeInsets.fromLTRB(
                    horizontal,
                    AppSpacing.lg,
                    horizontal,
                    AppSpacing.lg,
                  ),
                  children: [
                    Row(
                      children: [
                        IconButton(
                          tooltip: 'Back',
                          onPressed: () => context.go(
                            Uri(
                              path: '/welcome',
                              queryParameters: widget.redirect == null
                                  ? null
                                  : {'redirect': widget.redirect!},
                            ).toString(),
                          ),
                          icon: const VyaparIcon(VyaparIcons.back),
                        ),
                        const Expanded(child: VyaparLogo(height: 38)),
                        IconButton(
                          tooltip: 'Language',
                          onPressed: () => context.push('/language'),
                          icon: const VyaparIcon(VyaparIcons.language),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.xxl),
                    Text(
                      l10n.welcomeBack,
                      style: Theme.of(context).textTheme.displaySmall,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      l10n.signInBody,
                      style: Theme.of(
                        context,
                      ).textTheme.bodyLarge?.copyWith(color: AppColors.muted),
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    Form(
                      key: _formKey,
                      child: Column(
                        children: [
                          AppTextField(
                            fieldKey: const ValueKey('email_field'),
                            controller: _email,
                            label: l10n.emailAddress,
                            hint: 'you@example.com',
                            keyboardType: TextInputType.emailAddress,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.username],
                            prefixIcon: VyaparIcons.email,
                            validator: (value) {
                              final email = value?.trim() ?? '';
                              return email.contains('@')
                                  ? null
                                  : 'Enter a valid email address';
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          AppTextField(
                            fieldKey: const ValueKey('password_field'),
                            controller: _password,
                            label: l10n.password,
                            obscureText: _obscurePassword,
                            textInputAction: TextInputAction.done,
                            autofillHints: const [AutofillHints.password],
                            prefixIcon: VyaparIcons.password,
                            suffix: IconButton(
                              tooltip: _obscurePassword
                                  ? 'Show password'
                                  : 'Hide password',
                              onPressed: () => setState(
                                () => _obscurePassword = !_obscurePassword,
                              ),
                              icon: VyaparIcon(
                                _obscurePassword
                                    ? VyaparIcons.hidden
                                    : VyaparIcons.visible,
                                size: 20,
                              ),
                            ),
                            validator: (value) => (value?.isEmpty ?? true)
                                ? 'Enter your password'
                                : null,
                            onSubmitted: (_) => _submit(),
                          ),
                        ],
                      ),
                    ),
                    if (failure != null) ...[
                      const SizedBox(height: AppSpacing.md),
                      _SignInError(
                        message: failure is AppFailure
                            ? failure.message
                            : 'Sign in could not be completed.',
                      ),
                    ],
                    const SizedBox(height: AppSpacing.lg),
                    PrimaryButton(
                      key: const ValueKey('sign_in_button'),
                      label: l10n.signIn,
                      loading: auth.isLoading,
                      onPressed: _submit,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    SecondaryButton(
                      key: const ValueKey('otp_sign_in_button'),
                      label: 'Sign in with OTP',
                      onPressed: () => context.go('/otp'),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    SecondaryButton(
                      key: const ValueKey('google_sign_in_button'),
                      label: 'Continue with Google',
                      leading: SvgPicture.asset(
                        'assets/google.svg',
                        width: 20,
                        height: 20,
                      ),
                      loading: oauth.isLoading,
                      onPressed: () => _oauth('google'),
                    ),
                    if (oauth.hasError) ...[
                      const SizedBox(height: AppSpacing.sm),
                      _SignInError(message: oauth.error.toString()),
                    ],
                    const SizedBox(height: AppSpacing.lg),
                    Row(
                      children: [
                        const Expanded(child: Divider()),
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppSpacing.sm,
                          ),
                          child: Text(
                            'Or Register New Account',
                            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                              color: AppColors.muted,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const Expanded(child: Divider()),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Row(
                      children: [
                        Expanded(
                          child: _RegistrationOptionCard(
                            key: const ValueKey('create_account_button'),
                            icon: VyaparIcons.store,
                            title: 'Merchant\nRegistration',
                            subtitle: 'Kirana & Retail',
                            onTap: () => context.go('/otp?registration=true&role=merchant'),
                          ),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: _RegistrationOptionCard(
                            key: const ValueKey('supplier_registration_button'),
                            icon: VyaparIcons.truck,
                            title: 'Supplier\nRegistration',
                            subtitle: 'Wholesale B2B',
                            onTap: () => context.go('/otp?registration=true&role=supplier'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    ),
  );
  }
}

class _RegistrationOptionCard extends StatelessWidget {
  const _RegistrationOptionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    super.key,
  });

  final List<List<dynamic>> icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: AppColors.outline),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadii.md),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadii.md),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.md,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.paleBlue,
                    borderRadius: BorderRadius.circular(AppRadii.sm),
                  ),
                  child: VyaparIcon(icon, size: 20, color: AppColors.navy),
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.navy,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: AppColors.muted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SignInError extends StatelessWidget {
  const _SignInError({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const VyaparIcon(
          VyaparIcons.warning,
          color: AppColors.danger,
          size: 20,
        ),
        const SizedBox(width: AppSpacing.xs),
        Expanded(
          child: Text(
            message,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.danger),
          ),
        ),
      ],
    ),
  );
}
