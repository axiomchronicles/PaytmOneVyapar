import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';

class AppShell extends ConsumerWidget {
  const AppShell({required this.navigationShell, super.key});

  final StatefulNavigationShell navigationShell;

  void _goBranch(int index) {
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final offline = ref.watch(isOnlineProvider).value == false;
    final destinations = <_Destination>[
      const _Destination('Home', VyaparIcons.home),
      const _Destination('Insights', VyaparIcons.analytics),
      const _Destination('Munim AI', VyaparIcons.munim, isCenter: true),
      const _Destination('Orders', VyaparIcons.orders),
      const _Destination('More', VyaparIcons.more),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final rail = constraints.maxWidth >= 700;
        final content = SafeArea(
          bottom: false,
          child: Column(
            children: [
              NetworkBanner(visible: offline),
              Expanded(child: navigationShell),
            ],
          ),
        );
        if (rail) {
          return Scaffold(
            body: Row(
              children: [
                SafeArea(
                  child: NavigationRail(
                    selectedIndex: navigationShell.currentIndex,
                    onDestinationSelected: _goBranch,
                    labelType: constraints.maxWidth >= 920
                        ? NavigationRailLabelType.all
                        : NavigationRailLabelType.selected,
                    backgroundColor: AppColors.surface,
                    destinations: [
                      for (final item in destinations)
                        NavigationRailDestination(
                          icon: VyaparIcon(
                            item.icon,
                            key: ValueKey('nav_${item.label.toLowerCase()}'),
                          ),
                          selectedIcon: VyaparIcon(
                            item.icon,
                            color: AppColors.navy,
                          ),
                          label: Text(item.label),
                        ),
                    ],
                  ),
                ),
                const VerticalDivider(width: 1),
                Expanded(child: content),
              ],
            ),
          );
        }
        return Scaffold(
          body: content,
          bottomNavigationBar: NavigationBar(
            selectedIndex: navigationShell.currentIndex,
            onDestinationSelected: _goBranch,
            backgroundColor: AppColors.surface,
            indicatorColor: Colors.transparent,
            destinations: [
              for (final item in destinations)
                NavigationDestination(
                  icon: item.isCenter
                      ? Container(
                          padding: const EdgeInsets.all(7),
                          decoration: BoxDecoration(
                            color: AppColors.blue,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.blue.withValues(alpha: 0.35),
                                blurRadius: 8,
                                offset: const Offset(0, 3),
                              ),
                            ],
                          ),
                          child: VyaparIcon(
                            item.icon,
                            color: Colors.white,
                            size: 22,
                            key: const ValueKey('nav_munim'),
                          ),
                        )
                      : VyaparIcon(
                          item.icon,
                          color: AppColors.muted,
                          key: ValueKey('nav_${item.label.toLowerCase()}'),
                        ),
                  selectedIcon: item.isCenter
                      ? Container(
                          padding: const EdgeInsets.all(7),
                          decoration: BoxDecoration(
                            color: AppColors.navy,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.navy.withValues(alpha: 0.35),
                                blurRadius: 8,
                                offset: const Offset(0, 3),
                              ),
                            ],
                          ),
                          child: VyaparIcon(
                            item.icon,
                            color: Colors.white,
                            size: 22,
                          ),
                        )
                      : VyaparIcon(item.icon, color: AppColors.blue),
                  label: item.label,
                ),
            ],
          ),
        );
      },
    );
  }
}

class _Destination {
  const _Destination(this.label, this.icon, {this.isCenter = false});

  final String label;
  final List<List<dynamic>> icon;
  final bool isCenter;
}
