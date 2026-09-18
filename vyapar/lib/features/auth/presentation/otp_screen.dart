import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_text_field.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class OtpScreen extends ConsumerStatefulWidget {
  const OtpScreen({required this.registration, super.key});

  final bool registration;

  @override
  ConsumerState<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends ConsumerState<OtpScreen> {
  final _phone = TextEditingController();
  final _otp = TextEditingController();

  @override
  void dispose() {
    _phone.dispose();
    _otp.dispose();
    super.dispose();
  }

  Future<void> _verify(String value) async {
    try {
      final needsRegistration = await ref
          .read(otpFlowProvider.notifier)
          .verify(value, phone: _phone.text);
      if (mounted && needsRegistration) context.go('/register');
    } on Object {
      // The provider error is rendered below.
    }
  }

  @override
  Widget build(BuildContext context) {
    final flow = ref.watch(otpFlowProvider);
    final challenge = flow.value;
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/verify_otp_screen_bg.webp',
            fit: BoxFit.cover,
          ),
          SafeArea(
            child: CustomScrollView(
            slivers: [
              SliverFillRemaining(
                hasScrollBody: false,
                child: AdaptivePadding(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.registration
                            ? 'Verify your phone'
                            : 'Sign in with OTP',
                        style: Theme.of(context).textTheme.displaySmall,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        challenge == null
                            ? 'We’ll send a secure, short-lived code over the configured channel.'
                            : 'Enter the code sent to ${challenge.destination}.',
                      ),
                      const SizedBox(height: AppSpacing.xl),
                      if (challenge == null) ...[
                        AppTextField(
                          fieldKey: const ValueKey('otp_phone_field'),
                          controller: _phone,
                          label: 'Mobile number',
                          keyboardType: TextInputType.phone,
                        ),
                        const SizedBox(height: AppSpacing.md),
                        PrimaryButton(
                          key: const ValueKey('request_otp_button'),
                          label: 'Send OTP',
                          loading: flow.isLoading,
                          onPressed: () => ref
                              .read(otpFlowProvider.notifier)
                              .request(
                                _phone.text,
                                registration: widget.registration,
                              ),
                        ),
                      ] else ...[
                        OtpInput(controller: _otp, onCompleted: _verify),
                        const SizedBox(height: AppSpacing.md),
                        PrimaryButton(
                          key: const ValueKey('verify_otp_button'),
                          label: 'Verify',
                          loading: flow.isLoading,
                          onPressed: () => _verify(_otp.text),
                        ),
                        AppButton(
                          label: 'Resend code',
                          style: AppButtonStyle.text,
                          onPressed: ref.read(otpFlowProvider.notifier).resend,
                        ),
                      ],
                      if (flow.hasError) ...[
                        const SizedBox(height: AppSpacing.md),
                        AppErrorState(error: flow.error!),
                      ],
                      AppButton(
                        label: 'Back to sign in',
                        style: AppButtonStyle.text,
                        onPressed: () => context.go('/sign-in'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
  }
}
