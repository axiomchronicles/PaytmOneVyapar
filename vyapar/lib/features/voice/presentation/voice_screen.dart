import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/settings/providers/preferences_provider.dart';
import 'package:vyapar/features/voice/models/voice_models.dart';
import 'package:vyapar/features/voice/providers/voice_provider.dart';

class VoiceScreen extends ConsumerStatefulWidget {
  const VoiceScreen({super.key, this.approvalId, this.proposalId});

  final String? approvalId;
  final String? proposalId;

  @override
  ConsumerState<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends ConsumerState<VoiceScreen> {
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();
    _lifecycle = AppLifecycleListener(
      onPause: () =>
          unawaited(ref.read(voiceControllerProvider.notifier).stop()),
      onDetach: () =>
          unawaited(ref.read(voiceControllerProvider.notifier).stop()),
    );
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    final language = ref.read(languagePreferenceProvider).value ?? 'hi-IN';
    await ref
        .read(voiceControllerProvider.notifier)
        .start(
          languageCode: language,
          approvalId: widget.approvalId,
          proposalId: widget.proposalId,
        );
  }

  @override
  Widget build(BuildContext context) {
    final voice = ref.watch(voiceControllerProvider);
    final active = {
      VoicePhase.listening,
      VoicePhase.thinking,
      VoicePhase.speaking,
    }.contains(voice.phase);
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Voice Munim',
                  subtitle: _phaseLabel(voice.phase),
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                  trailing: active
                      ? IconAction(
                          icon: VyaparIcons.reject,
                          label: 'End session',
                          onPressed: ref
                              .read(voiceControllerProvider.notifier)
                              .stop,
                        )
                      : null,
                ),
              ),
            ),
            SliverFillRemaining(
              hasScrollBody: false,
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: voice.phase == VoicePhase.permissionDenied
                    ? PermissionPrompt(onRequest: _start)
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          VoiceOrb(active: active),
                          const SizedBox(height: AppSpacing.xl),
                          if (voice.transcript.isNotEmpty)
                            VoiceTranscript(
                              text: '“${voice.transcript}”',
                              partial: voice.phase == VoicePhase.listening,
                            )
                          else
                            Text(
                              active
                                  ? 'Speak naturally to your Munim'
                                  : 'Ready when you are',
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          if (voice.response.isNotEmpty) ...[
                            const SizedBox(height: AppSpacing.lg),
                            Text(
                              voice.response,
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.bodyLarge
                                  ?.copyWith(color: AppColors.navy),
                            ),
                          ],
                          if (!voice.playbackSupported &&
                              voice.phase == VoicePhase.speaking) ...[
                            const SizedBox(height: AppSpacing.md),
                            Text(
                              'The server is streaming MP3 without framing metadata. Transcript remains live; configure both ends for linear16 to enable continuous playback.',
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.bodyMedium
                                  ?.copyWith(color: AppColors.warning),
                            ),
                          ],
                          if (voice.errorMessage case final error?) ...[
                            const SizedBox(height: AppSpacing.md),
                            Text(
                              error,
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.bodyMedium
                                  ?.copyWith(color: AppColors.danger),
                            ),
                          ],
                          const SizedBox(height: AppSpacing.xl),
                          if (!active)
                            PrimaryButton(
                              key: const ValueKey('voice_connect_button'),
                              label: voice.phase == VoicePhase.connecting
                                  ? 'Connecting…'
                                  : 'Start voice session',
                              loading:
                                  voice.phase == VoicePhase.connecting ||
                                  voice.phase ==
                                      VoicePhase.requestingPermission,
                              onPressed: _start,
                            )
                          else if (voice.phase == VoicePhase.speaking)
                            DangerButton(
                              key: const ValueKey('voice_interrupt_button'),
                              label: 'Interrupt Munim',
                              leading: const VyaparIcon(
                                VyaparIcons.reject,
                                color: Colors.white,
                              ),
                              onPressed: ref
                                  .read(voiceControllerProvider.notifier)
                                  .interrupt,
                            ),
                        ],
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _phaseLabel(VoicePhase phase) => switch (phase) {
    VoicePhase.idle => 'Ready',
    VoicePhase.requestingPermission => 'Requesting microphone access',
    VoicePhase.permissionDenied => 'Permission denied',
    VoicePhase.connecting => 'Connecting securely',
    VoicePhase.listening => 'Listening…',
    VoicePhase.thinking => 'Checking your business…',
    VoicePhase.speaking => 'Munim is speaking',
    VoicePhase.interrupted => 'Interrupted',
    VoicePhase.disconnected => 'Disconnected',
    VoicePhase.error => 'Voice unavailable',
  };
}
