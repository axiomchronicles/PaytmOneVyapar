import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/app_text_field.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class RegistrationScreen extends ConsumerStatefulWidget {
  const RegistrationScreen({super.key});

  @override
  ConsumerState<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends ConsumerState<RegistrationScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _business = TextEditingController();
  final _store = TextEditingController();
  final _password = TextEditingController();

  @override
  void initState() {
    super.initState();
    _email.text = ref.read(pendingRegistrationProvider)?.email ?? '';
  }

  @override
  void dispose() {
    _email.dispose();
    _business.dispose();
    _store.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    await ref
        .read(registrationControllerProvider.notifier)
        .register(
          email: _email.text,
          businessName: _business.text,
          storeName: _store.text,
          password: _password.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    final pending = ref.watch(pendingRegistrationProvider);
    final registration = ref.watch(registrationControllerProvider);
    if (pending == null) {
      return Scaffold(
        body: SafeArea(
          child: EmptyState(
            title: 'Verification required',
            message:
                'Verify a phone number or OAuth identity before creating a business.',
            actionLabel: 'Start verification',
            onAction: () => context.go('/otp?registration=true'),
          ),
        ),
      );
    }
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Create your business',
                  subtitle: 'Verified identity, real merchant workspace',
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: Form(
                  key: _form,
                  child: Column(
                    children: [
                      AppTextField(
                        fieldKey: const ValueKey('registration_email'),
                        controller: _email,
                        label: 'Email address',
                        enabled: pending.email == null,
                        keyboardType: TextInputType.emailAddress,
                        validator: (value) => (value?.contains('@') ?? false)
                            ? null
                            : 'Enter a valid email address',
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_business'),
                        controller: _business,
                        label: 'Business name',
                        validator: (value) => (value?.trim().length ?? 0) >= 2
                            ? null
                            : 'Enter your business name',
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_store'),
                        controller: _store,
                        label: 'First store name',
                        validator: (value) => (value?.trim().length ?? 0) >= 2
                            ? null
                            : 'Enter your store name',
                      ),
                      if (!pending.oauth) ...[
                        const SizedBox(height: AppSpacing.md),
                        AppTextField(
                          fieldKey: const ValueKey('registration_password'),
                          controller: _password,
                          label: 'Password',
                          obscureText: true,
                          validator: (value) => (value?.length ?? 0) >= 12
                              ? null
                              : 'Use at least 12 characters',
                        ),
                      ],
                      if (registration.hasError) ...[
                        const SizedBox(height: AppSpacing.md),
                        AppErrorState(error: registration.error!),
                      ],
                      const SizedBox(height: AppSpacing.lg),
                      PrimaryButton(
                        key: const ValueKey('register_button'),
                        label: 'Create business',
                        loading: registration.isLoading,
                        onPressed: _submit,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
