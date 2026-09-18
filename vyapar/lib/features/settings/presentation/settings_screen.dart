import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/settings/presentation/language_screen.dart';
import 'package:vyapar/features/settings/providers/preferences_provider.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final languageCode = ref.watch(languagePreferenceProvider).value ?? 'auto';
    final language = supportedVoiceLanguages
        .where((item) => item.$1 == languageCode)
        .firstOrNull
        ?.$2;
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Settings',
                  subtitle: 'Preferences supported by this app',
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                ),
              ),
            ),
            SliverList.list(
              children: [
                ListTile(
                  leading: const VyaparIcon(
                    VyaparIcons.language,
                    color: AppColors.blue,
                  ),
                  title: const Text('Voice language'),
                  subtitle: Text(language ?? 'Automatic'),
                  trailing: const VyaparIcon(VyaparIcons.forward, size: 18),
                  onTap: () => context.push('/language'),
                ),
                const Divider(indent: 64),
                const ListTile(
                  leading: VyaparIcon(
                    VyaparIcons.notification,
                    color: AppColors.muted,
                  ),
                  title: Text('Notification preferences'),
                  subtitle: Text('Waiting for a backend settings contract'),
                  enabled: false,
                ),
                const Divider(indent: 64),
                const ListTile(
                  leading: VyaparIcon(
                    VyaparIcons.security,
                    color: AppColors.muted,
                  ),
                  title: Text('Security'),
                  subtitle: Text('Managed by backend authentication policy'),
                  enabled: false,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
