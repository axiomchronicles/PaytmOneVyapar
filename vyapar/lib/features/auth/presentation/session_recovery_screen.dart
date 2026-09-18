import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class SessionRecoveryScreen extends ConsumerWidget {
  const SessionRecoveryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    body: SafeArea(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Expanded(
            child: AppErrorState(
              error:
                  ref.watch(authControllerProvider).error ??
                  StateError('Session validation failed.'),
              onRetry: ref.read(authControllerProvider.notifier).retryRestore,
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24),
            child: SecondaryButton(
              label: 'Sign in again',
              onPressed: ref.read(authControllerProvider.notifier).signOut,
            ),
          ),
        ],
      ),
    ),
  );
}
