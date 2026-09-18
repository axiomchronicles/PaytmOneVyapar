import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class MoreScreen extends ConsumerWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => CustomScrollView(
    key: const PageStorageKey('more_scroll'),
    slivers: [
      const SliverPadding(
        padding: EdgeInsets.all(AppSpacing.md),
        sliver: SliverToBoxAdapter(
          child: AppHeader(
            title: 'More',
            subtitle: 'Business and app settings',
          ),
        ),
      ),
      SliverList.list(
        children: [
          _MoreItem(
            icon: VyaparIcons.profile,
            title: 'Business profile',
            onTap: () => context.push('/more/profile'),
          ),
          _MoreItem(
            icon: VyaparIcons.analytics,
            title: 'Analytics',
            onTap: () => context.push('/analytics'),
          ),
          _MoreItem(
            icon: VyaparIcons.settings,
            title: 'Settings',
            onTap: () => context.push('/more/settings'),
          ),
          _MoreItem(
            icon: VyaparIcons.info,
            title: 'Backend capabilities',
            onTap: () => context.push('/more/capabilities'),
          ),
          _MoreItem(
            icon: VyaparIcons.logout,
            title: 'Sign out',
            onTap: ref.read(authControllerProvider.notifier).signOut,
          ),
        ],
      ),
      const SliverPadding(padding: EdgeInsets.only(bottom: 110)),
    ],
  );
}

class _MoreItem extends StatelessWidget {
  const _MoreItem({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  final List<List<dynamic>> icon;
  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      ListTile(
        minTileHeight: 64,
        leading: VyaparIcon(icon, color: AppColors.navy),
        title: Text(title),
        trailing: const VyaparIcon(VyaparIcons.forward, size: 18),
        onTap: onTap,
      ),
      const Divider(indent: 64),
    ],
  );
}
