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
      _Destination('Home', VyaparIcons.home),
      _Destination('Inventory', VyaparIcons.inventory),
      _Destination('Munim', VyaparIcons.munim),
      _Destination('Orders', VyaparIcons.orders),
      _Destination('More', VyaparIcons.more),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final rail = constraints.maxWidth >= 700;
        final content = Column(
          children: [
            NetworkBanner(visible: offline),
            Expanded(child: navigationShell),
          ],
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
            destinations: [
              for (final item in destinations)
                NavigationDestination(
                  icon: VyaparIcon(
                    item.icon,
                    key: ValueKey('nav_${item.label.toLowerCase()}'),
                  ),
                  selectedIcon: VyaparIcon(item.icon, color: AppColors.navy),
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
  const _Destination(this.label, this.icon);

  final String label;
  final List<List<dynamic>> icon;
}
