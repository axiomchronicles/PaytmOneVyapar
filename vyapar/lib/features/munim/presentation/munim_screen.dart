import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/data_components.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/inventory/models/inventory_item.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class MunimScreen extends ConsumerWidget {
  const MunimScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inventory = ref.watch(inventoryControllerProvider);
    final recommendations = ref.watch(recommendationControllerProvider);
    final isLoading = inventory.isLoading || recommendations.isLoading;
    final lowItems = (inventory.value ?? const <InventoryItem>[])
        .where((item) => item.isLow)
        .toList(growable: false);
    return CustomScrollView(
      key: const PageStorageKey('munim_scroll'),
      slivers: [
        const SliverSection(child: SizedBox(height: AppSpacing.sm)),
        const SliverSection(
          child: AppHeader(
            title: 'Munim',
            subtitle: 'Your business assistant, grounded in live shop data',
            leading: VyaparIcon(VyaparIcons.munim, color: AppColors.navy),
          ),
        ),
        const SliverSection(child: SizedBox(height: AppSpacing.lg)),
        SliverSection(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(AppRadii.lg),
            child: AspectRatio(
              aspectRatio: 1230 / 1278,
              child: Image.asset(
                'assets/munim_ai_bg.webp',
                fit: BoxFit.contain,
              ),
            ),
          ),
        ),
        const SliverSection(child: SizedBox(height: AppSpacing.lg)),
        SliverSection(
          child: PrimaryButton(
            key: const ValueKey('start_voice_button'),
            label: 'Talk to Munim',
            leading: const VyaparIcon(VyaparIcons.mic, color: Colors.white),
            onPressed: () => context.push('/voice'),
          ),
        ),
        const SliverSection(child: SizedBox(height: AppSpacing.xl)),
        const SliverSection(child: SectionHeader(title: 'Needs attention')),
        const SliverSection(child: SizedBox(height: AppSpacing.xs)),
        if (isLoading)
          const SliverSection(child: ListSkeleton(rows: 3))
        else if (inventory.hasError || recommendations.hasError)
          SliverSection(
            child: AppErrorState(
              error: inventory.error ?? recommendations.error!,
              onRetry: () {
                ref.invalidate(inventoryControllerProvider);
                ref.invalidate(recommendationControllerProvider);
              },
            ),
          )
        else if (lowItems.isEmpty)
          const SliverFillRemaining(
            hasScrollBody: false,
            child: EmptyState(
              title: 'Nothing urgent',
              message: 'Munim has no low-stock signal right now.',
            ),
          )
        else
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            sliver: SliverList.separated(
              itemCount: lowItems.length,
              separatorBuilder: (context, index) => const Divider(indent: 52),
              itemBuilder: (context, index) {
                final item = lowItems[index];
                return ListTile(
                  leading: const VyaparIcon(
                    VyaparIcons.warning,
                    color: AppColors.warning,
                  ),
                  title: Text(item.name),
                  subtitle: Text(
                    '${formatQuantity(item.quantityOnHand)} ${item.unit} on hand · reorder at ${formatQuantity(item.reorderPoint)}',
                  ),
                  trailing: const VyaparIcon(VyaparIcons.forward, size: 18),
                  onTap: () => context.push('/inventory/${item.inventoryId}'),
                );
              },
            ),
          ),
        const SliverPadding(padding: EdgeInsets.only(bottom: 110)),
      ],
    );
  }
}
