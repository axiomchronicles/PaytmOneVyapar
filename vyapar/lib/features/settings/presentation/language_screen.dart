import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/settings/providers/preferences_provider.dart';

const supportedVoiceLanguages = <(String, String)>[
  ('auto', 'Automatic'),
  ('en-IN', 'English'),
  ('hi-IN', 'हिन्दी'),
  ('gu-IN', 'ગુજરાતી'),
  ('bn-IN', 'বাংলা'),
  ('bho-IN', 'भोजपुरी'),
  ('ta-IN', 'தமிழ்'),
  ('te-IN', 'తెలుగు'),
  ('mr-IN', 'मराठी'),
];

class LanguageScreen extends ConsumerWidget {
  const LanguageScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(languagePreferenceProvider).value ?? 'auto';
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Voice language',
                  subtitle: 'Used for new Munim voice sessions',
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: context.pop,
                  ),
                ),
              ),
            ),
            SliverList.separated(
              itemCount: supportedVoiceLanguages.length,
              separatorBuilder: (context, index) => const Divider(indent: 64),
              itemBuilder: (context, index) {
                final language = supportedVoiceLanguages[index];
                final active = selected == language.$1;
                return Semantics(
                  selected: active,
                  child: ListTile(
                    minTileHeight: 60,
                    leading: VyaparIcon(
                      VyaparIcons.language,
                      color: active ? AppColors.blue : AppColors.muted,
                    ),
                    title: Text(language.$2),
                    trailing: active
                        ? const VyaparIcon(
                            VyaparIcons.success,
                            color: AppColors.success,
                          )
                        : null,
                    onTap: () => ref
                        .read(languagePreferenceProvider.notifier)
                        .select(language.$1),
                  ),
                );
              },
            ),
            const SliverPadding(
              padding: EdgeInsets.only(bottom: AppSpacing.xl),
            ),
          ],
        ),
      ),
    );
  }
}
