import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/components/vyapar_logo.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/features/analytics/providers/analytics_provider.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';
import 'package:vyapar/features/profile/providers/merchant_provider.dart';
import 'package:vyapar/features/recommendations/providers/recommendation_provider.dart';
import 'package:vyapar/shared/formatters/formatters.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    await Future.wait([
      ref.read(merchantControllerProvider.notifier).refresh(),
      ref.read(inventoryControllerProvider.notifier).refresh(),
      ref.read(recommendationControllerProvider.notifier).refresh(),
      ref.read(analyticsControllerProvider.notifier).refresh(),
    ]);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => SafeArea(
    top: true,
    bottom: false,
    child: RefreshIndicator(
      onRefresh: () => _refresh(ref),
      child: CustomScrollView(
        key: const PageStorageKey('home_scroll'),
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: const [
          SliverSection(child: _MerchantTopBar()),
          SliverSection(child: SizedBox(height: 12)),
          SliverSection(child: _MerchantQuickActionsStrip()),
          SliverSection(child: SizedBox(height: 14)),
          SliverSection(child: _CriticalStockAlert()),
          SliverSection(child: SizedBox(height: 14)),
          SliverSection(child: _AajKaHaalContainerCard()),
          SliverSection(child: SizedBox(height: 14)),
          SliverSection(child: _MerchantProcurementAndDealsCard()),
          SliverSection(child: SizedBox(height: 14)),
          SliverSection(child: _OpportunitiesSection()),
          SliverSection(child: SizedBox(height: 14)),
          SliverSection(child: _MunimVoiceBanner()),
          SliverPadding(padding: EdgeInsets.only(bottom: 24)),
        ],
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// 1. Premium Merchant Top Bar (Avatar + Brand & Store Dropdown + Search + Bell)
// ---------------------------------------------------------------------------
class _MerchantTopBar extends ConsumerWidget {
  const _MerchantTopBar();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(merchantControllerProvider);
    final initials = profile.when(
      data: (p) => p.initials,
      loading: () => 'RS',
      error: (_, _) => 'RS',
    );
    final storeName = profile.when(
      data: (p) => p.name,
      loading: () => 'Sharma General Store',
      error: (_, _) => 'Sharma General Store',
    );
    final locality = profile.when(
      data: (p) => p.stores.firstOrNull?.locality ?? 'Karol Bagh, New Delhi',
      loading: () => 'Karol Bagh, New Delhi',
      error: (_, _) => 'Karol Bagh, New Delhi',
    );

    return Padding(
      padding: const EdgeInsets.only(top: 4, bottom: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Merchant Initials Avatar Circle (coral pink with deep crimson text)
          InkWell(
            onTap: () => context.push('/more/profile'),
            borderRadius: BorderRadius.circular(22),
            child: Container(
              width: 42,
              height: 42,
              decoration: const BoxDecoration(
                color: Color(0xFFFFD5D6),
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  initials,
                  style: const TextStyle(
                    color: Color(0xFFBA1A1A),
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),

          // Center: Paytm One | Vyapar branding + Store selector dropdown
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const VyaparLogo(height: 21),
                const SizedBox(height: 2),
                InkWell(
                  onTap: () => _showStoreBottomSheet(context, storeName, locality),
                  borderRadius: BorderRadius.circular(8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Flexible(
                        child: Text(
                          storeName,
                          style: const TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF1D232C),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 2),
                      const Icon(
                        Icons.keyboard_arrow_down_rounded,
                        size: 16,
                        color: Color(0xFF64748B),
                      ),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          '• $locality',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xFF64748B),
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),

          // Right: Search and Notification Bell
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                tooltip: 'Search Inventory & Orders',
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                onPressed: () => context.push('/inventory'),
                icon: const Icon(
                  Icons.search_rounded,
                  size: 24,
                  color: Color(0xFF1D232C),
                ),
              ),
              IconButton(
                tooltip: 'Notifications',
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                onPressed: () => context.push('/notifications'),
                icon: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    const Icon(
                      Icons.notifications_none_rounded,
                      size: 24,
                      color: Color(0xFF1D232C),
                    ),
                    Positioned(
                      top: 1,
                      right: 1,
                      child: Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: Color(0xFFE51A4C),
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// 2. Vyapar Quick Actions (4 Solid Deep Paytm Blue Action Circles)
// ---------------------------------------------------------------------------
class _MerchantQuickActionsStrip extends ConsumerWidget {
  const _MerchantQuickActionsStrip();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(merchantControllerProvider).value;
    final analytics = ref.watch(analyticsControllerProvider).value;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Jaldi karein (Quick Actions)',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w800,
            color: Color(0xFF1D232C),
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _MerchantCircleAction(
                icon: Icons.qr_code_scanner_rounded,
                label: 'Payment\nQR / Soundbox',
                onTap: () => _showPaymentQrSheet(context, profile),
              ),
            ),
            Expanded(
              child: _MerchantCircleAction(
                icon: Icons.account_balance_wallet_outlined,
                label: 'Settlements\n& Payouts',
                onTap: () => _showSettlementsSheet(
                  context,
                  analytics?.expectedSettlement ?? 17980.0,
                ),
              ),
            ),
            Expanded(
              child: _MerchantCircleAction(
                icon: Icons.inventory_2_outlined,
                label: 'Stock &\nInventory',
                onTap: () => context.push('/inventory'),
              ),
            ),
            Expanded(
              child: _MerchantCircleAction(
                icon: Icons.smart_toy_outlined,
                label: 'Munim AI\nAssistant',
                onTap: () => context.push('/munim'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _MerchantCircleAction extends StatelessWidget {
  const _MerchantCircleAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Center(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: const BoxDecoration(
              color: Color(0xFF002E6E),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Color(0x1F002E6E),
                  blurRadius: 6,
                  offset: Offset(0, 3),
                ),
              ],
            ),
            child: Center(
              child: Icon(icon, color: Colors.white, size: 26),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              color: Color(0xFF1E293B),
              height: 1.15,
            ),
            maxLines: 2,
          ),
        ],
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// 3. Critical Stock Alert ("Dhyaan dene layak")
// ---------------------------------------------------------------------------
class _CriticalStockAlert extends ConsumerWidget {
  const _CriticalStockAlert();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inventory = ref.watch(inventoryControllerProvider);
    final lowCount = inventory.value?.where((item) => item.isLow).length;
    final firstLow = inventory.value?.where((item) => item.isLow).firstOrNull;

    final signalSubtext = switch ((inventory.isLoading, lowCount)) {
      (true, _) => 'Checking your shop now…',
      (_, null) => 'Sirf 12 units bache hain. Is weekend demand 28% zyada rehne ki sambhaavna hai.',
      (_, 0) => 'No inventory item is below its reorder point.',
      (_, final count) =>
        '$count inventory ${count == 1 ? 'item needs' : 'items need'} attention.',
    };

    final title = firstLow != null
        ? '${firstLow.name} ka stock kal tak khatam ho sakta hai'
        : 'Cold drinks ka stock kal tak khatam ho sakta hai';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.035),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: const Color(0xFFFFECEB),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Center(
              child: Icon(
                Icons.local_drink_rounded,
                color: Color(0xFFC92A2A),
                size: 24,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.error_outline_rounded,
                      color: AppColors.danger,
                      size: 13,
                    ),
                    SizedBox(width: 4),
                    Flexible(
                      child: Text(
                        'Dhyaan dene layak',
                        style: TextStyle(
                          color: AppColors.danger,
                          fontWeight: FontWeight.w700,
                          fontSize: 11,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF1D232C),
                    height: 1.2,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  signalSubtext,
                  style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFF64748B),
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          TextButton(
            onPressed: () => context.push('/inventory'),
            style: TextButton.styleFrom(
              backgroundColor: const Color(0xFFFFECEB),
              foregroundColor: const Color(0xFFC92A2A),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              visualDensity: VisualDensity.compact,
            ),
            child: const Text(
              'Review →',
              style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// 4. "Aaj ka haal" Merchant Pulse Container Card (Clean white rounded container)
// ---------------------------------------------------------------------------
class _AajKaHaalContainerCard extends ConsumerWidget {
  const _AajKaHaalContainerCard();

  String _formatTodayDate() {
    const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    final now = DateTime.now();
    return '${weekdays[now.weekday - 1]}, ${now.day} ${months[now.month - 1]} ${now.year}';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analytics = ref.watch(analyticsControllerProvider).value;
    final totalSales = analytics?.totalSalesAmount ?? 18420.0;
    final salesGrowth = analytics?.salesGrowthPct ?? 12.0;
    final customerCount = analytics?.customerCount ?? 146;
    final expectedSettlement = analytics?.expectedSettlement ?? 17980.0;

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.035),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Text(
                  'Aaj ka haal',
                  style: TextStyle(
                    fontSize: 17.5,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF1D232C),
                    letterSpacing: -0.2,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                _formatTodayDate(),
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: AppColors.muted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _PulseMetricTile(
                  icon: VyaparIcons.chartUp,
                  iconColor: AppColors.success,
                  title: 'Total Sales',
                  value: '₹${formatInr(totalSales)}',
                  badgeText: '↑ ${salesGrowth.toStringAsFixed(0)}% Kal se zyada',
                  badgeColor: AppColors.success,
                  onTap: () => context.push('/analytics'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _PulseMetricTile(
                  icon: VyaparIcons.userGroup,
                  iconColor: AppColors.blue,
                  title: 'Customers',
                  value: '$customerCount',
                  badgeText: '↑ 8% Kal se zyada',
                  badgeColor: AppColors.blue,
                  onTap: () => context.push('/analytics'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _PulseMetricTile(
                  icon: VyaparIcons.wallet,
                  iconColor: const Color(0xFF007AEB),
                  title: 'Settlement (Expected)',
                  value: '₹${formatInr(expectedSettlement)}',
                  badgeText: 'Aaj 4:00 PM tak',
                  badgeColor: const Color(0xFF007AEB),
                  onTap: () => _showSettlementsSheet(context, expectedSettlement),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _PulseMetricTile(
                  icon: VyaparIcons.inventory,
                  iconColor: const Color(0xFFE06D10),
                  title: 'Low Stock Items',
                  value: '3',
                  badgeText: 'Action needed →',
                  badgeColor: AppColors.danger,
                  onTap: () => context.push('/inventory'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Center(
            child: Container(
              width: 32,
              height: 4,
              decoration: BoxDecoration(
                color: const Color(0xFFDCE5EF),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PulseMetricTile extends StatelessWidget {
  const _PulseMetricTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.value,
    required this.badgeText,
    required this.badgeColor,
    required this.onTap,
  });

  final List<List<dynamic>> icon;
  final Color iconColor;
  final String title;
  final String value;
  final String badgeText;
  final Color badgeColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(12),
    child: Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFF64748B),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 4),
              VyaparIcon(icon, size: 15, color: iconColor),
            ],
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: const TextStyle(
              fontSize: 16.5,
              fontWeight: FontWeight.w800,
              color: Color(0xFF1D232C),
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            badgeText,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: badgeColor,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// 5. Merchant Procurement & Wholesale Deals Card (A2A & Bulk purchasing)
// ---------------------------------------------------------------------------
class _MerchantProcurementAndDealsCard extends StatelessWidget {
  const _MerchantProcurementAndDealsCard();

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: InkWell(
          onTap: () => context.push('/suppliers'),
          borderRadius: BorderRadius.circular(18),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.035),
                  blurRadius: 10,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              children: [
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'A2A Suppliers',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF1D232C),
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Compare prices &\norder direct stock',
                        style: TextStyle(
                          fontSize: 10.5,
                          color: Color(0xFF64748B),
                          height: 1.2,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 6),
                Container(
                  width: 38,
                  height: 38,
                  decoration: const BoxDecoration(
                    color: Color(0xFFF0F6FE),
                    shape: BoxShape.circle,
                  ),
                  child: const Center(
                    child: VyaparIcon(
                      VyaparIcons.truck,
                      size: 20,
                      color: Color(0xFF007AEB),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      const SizedBox(width: 10),
      Expanded(
        child: InkWell(
          onTap: () => context.push('/negotiations'),
          borderRadius: BorderRadius.circular(18),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.035),
                  blurRadius: 10,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              children: [
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Bulk Discounts',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF1D232C),
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Wholesale deals &\nsavings on crates',
                        style: TextStyle(
                          fontSize: 10.5,
                          color: Color(0xFF64748B),
                          height: 1.2,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 6),
                Container(
                  width: 38,
                  height: 38,
                  decoration: const BoxDecoration(
                    color: Color(0xFFFFF7ED),
                    shape: BoxShape.circle,
                  ),
                  child: const Center(
                    child: VyaparIcon(
                      VyaparIcons.tag,
                      size: 20,
                      color: Color(0xFFF59E0B),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ],
  );
}

// ---------------------------------------------------------------------------
// 6. "Aapke liye mauke" (Actionable AI Recommendations)
// ---------------------------------------------------------------------------
class _OpportunitiesSection extends ConsumerWidget {
  const _OpportunitiesSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendations = ref.watch(recommendationControllerProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Expanded(
              child: Text(
                'Aapke liye mauke',
                style: TextStyle(
                  fontSize: 17.5,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF1D232C),
                  letterSpacing: -0.2,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            InkWell(
              onTap: () => context.push('/recommendations'),
              child: const Text(
                'Sab dekhein >',
                style: TextStyle(
                  fontSize: 12.5,
                  color: Color(0xFF007AEB),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        recommendations.when(
          loading: () => const ListSkeleton(rows: 2),
          error: (error, _) => AppErrorState(
            error: error,
            onRetry: ref.read(recommendationControllerProvider.notifier).refresh,
          ),
          data: (items) {
            if (items.isEmpty) {
              return const EmptyState(
                title: 'No new recommendations',
                message: 'Munim has no new recommendations right now.',
              );
            }
            return SizedBox(
              height: 175,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                physics: const BouncingScrollPhysics(),
                itemCount: items.length < 3 ? 3 : items.length,
                separatorBuilder: (context, index) => const SizedBox(width: 10),
                itemBuilder: (context, index) {
                  if (index < items.length) {
                    final item = items[index];
                    return _OpportunityCard(
                      icon: index == 0
                          ? VyaparIcons.chartUp
                          : (index == 1 ? VyaparIcons.truck : VyaparIcons.tag),
                      iconColor: index == 0
                          ? AppColors.blue
                          : (index == 1 ? AppColors.success : const Color(0xFFE06D10)),
                      iconBg: index == 0
                          ? AppColors.paleBlue
                          : (index == 1 ? const Color(0xFFE8F7F0) : const Color(0xFFFFF2E6)),
                      title: index == 0
                          ? 'Weekend offer chalayein cold drinks par'
                          : (index == 1
                              ? '3 crates kharidein 5% kam daam par'
                              : 'Cricket match ke chalte sales badh rahi hain'),
                      subtitle: index == 0
                          ? '₹5,000+ tak extra revenue ki sambhaavna'
                          : (index == 1
                              ? 'North Delhi Distributor Se ₹375 ki bachat'
                              : 'Aaj hi local customers ko target karein'),
                      sku: item.sku,
                      actionLabel: index == 0
                          ? 'Offer Banayein →'
                          : (index == 1 ? 'Deal Dekhein →' : 'Campaign Chalayein →'),
                      onAction: () {
                        if (index == 1) {
                          context.push('/negotiations');
                        } else {
                          _showCampaignDialog(
                            context,
                            title: index == 0
                                ? 'Weekend Offer on ${item.sku}'
                                : 'Cricket Match Day Special',
                          );
                        }
                      },
                    );
                  }
                  return _OpportunityCard(
                    icon: VyaparIcons.tag,
                    iconColor: const Color(0xFFE06D10),
                    iconBg: const Color(0xFFFFF2E6),
                    title: 'Cricket match ke chalte sales badh rahi hain',
                    subtitle: 'Aaj hi local customers ko target karein',
                    actionLabel: 'Campaign Chalayein →',
                    onAction: () => _showCampaignDialog(
                      context,
                      title: 'Cricket Match Day Special',
                    ),
                  );
                },
              ),
            );
          },
        ),
      ],
    );
  }
}

class _OpportunityCard extends StatelessWidget {
  const _OpportunityCard({
    required this.icon,
    required this.iconColor,
    required this.iconBg,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.onAction,
    this.sku,
  });

  final List<List<dynamic>> icon;
  final Color iconColor;
  final Color iconBg;
  final String title;
  final String subtitle;
  final String actionLabel;
  final VoidCallback onAction;
  final String? sku;

  @override
  Widget build(BuildContext context) => Container(
    width: 250,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.035),
          blurRadius: 10,
          offset: const Offset(0, 2),
        ),
      ],
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: iconBg,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: VyaparIcon(icon, size: 18, color: iconColor),
              ),
            ),
            if (sku case final code?)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.paleBlue,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  code,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: AppColors.navy,
                  ),
                ),
              ),
          ],
        ),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF1D232C),
                height: 1.2,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 3),
            Text(
              subtitle,
              style: const TextStyle(
                fontSize: 10.5,
                color: Color(0xFF64748B),
                height: 1.15,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: onAction,
            style: TextButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              foregroundColor: const Color(0xFF007AEB),
            ),
            child: Text(
              actionLabel,
              style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
            ),
          ),
        ),
      ],
    ),
  );
}

// ---------------------------------------------------------------------------
// 7. Munim AI Voice Assistant Floating Banner CTA
// ---------------------------------------------------------------------------
class _MunimVoiceBanner extends StatelessWidget {
  const _MunimVoiceBanner();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    decoration: BoxDecoration(
      color: const Color(0xFFEBF5FE),
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: const Color(0xFFCBE5FD)),
    ),
    child: Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: const BoxDecoration(
            color: Color(0xFF007AEB),
            shape: BoxShape.circle,
          ),
          child: const Center(
            child: VyaparIcon(VyaparIcons.mic, size: 19, color: Colors.white),
          ),
        ),
        const SizedBox(width: 10),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Munim AI se baat karein',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF1D232C),
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              SizedBox(height: 1),
              Text(
                'Apne sawaal poochhein, order place karein ya stock insights paayein.',
                style: TextStyle(
                  fontSize: 10.5,
                  color: Color(0xFF64748B),
                  height: 1.2,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Flexible(
          child: OutlinedButton.icon(
            onPressed: () => context.push('/voice'),
            icon: const VyaparIcon(VyaparIcons.mic, size: 12, color: Color(0xFF007AEB)),
            label: const Text(
              'Voice Par Baat Karein',
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF007AEB),
              side: const BorderSide(color: Color(0xFF007AEB)),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            ),
          ),
        ),
      ],
    ),
  );
}

// ---------------------------------------------------------------------------
// Helper Dialogs and Bottom Sheets
// ---------------------------------------------------------------------------
void _showPaymentQrSheet(BuildContext context, MerchantProfile? profile) {
  final merchantName = profile?.name ?? 'Sharma General Store';
  final storeName = profile?.stores.firstOrNull?.name ?? 'Main Store';
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (context) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const VyaparLogo(height: 24),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              storeName,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            Text(
              merchantName,
              style: const TextStyle(fontSize: 13, color: AppColors.muted),
            ),
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.blue, width: 2),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.blue.withValues(alpha: 0.08),
                    blurRadius: 16,
                  ),
                ],
              ),
              child: Column(
                children: [
                  const Icon(
                    Icons.qr_code_2_rounded,
                    size: 180,
                    color: AppColors.navy,
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.paleBlue,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.volume_up, size: 14, color: AppColors.blue),
                        SizedBox(width: 5),
                        Text(
                          'Paytm Soundbox Active',
                          style: TextStyle(
                            fontSize: 11.5,
                            color: AppColors.navy,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'UPI ID: paytm-merchant@paytm',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppColors.muted,
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.blue,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                onPressed: () => Navigator.pop(context),
                child: const Text('Done'),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

void _showSettlementsSheet(BuildContext context, double expected) {
  showModalBottomSheet<void>(
    context: context,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (context) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Today’s Settlement',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.paleBlue,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Expected Settlement',
                    style: TextStyle(fontSize: 12, color: AppColors.muted),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '₹${formatInr(expected)}',
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      color: AppColors.navy,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Row(
                    children: [
                      Icon(Icons.schedule, size: 14, color: AppColors.blue),
                      SizedBox(width: 4),
                      Text(
                        'Estimated credit by 4:00 PM today',
                        style: TextStyle(fontSize: 11.5, color: AppColors.blue),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.account_balance, color: AppColors.navy),
              title: Text('HDFC Bank •••• 4921'),
              subtitle: Text('Primary Settlement Account • Instant Payout Active'),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () {
                  Navigator.pop(context);
                  context.push('/analytics');
                },
                child: const Text('View Full Financial Insights'),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

void _showStoreBottomSheet(BuildContext context, String name, String locality) {
  showModalBottomSheet<void>(
    context: context,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (context) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const VyaparIcon(VyaparIcons.store, color: AppColors.navy, size: 22),
                const SizedBox(width: 10),
                Text(
                  'Selected Store',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppColors.navy,
                      ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppColors.paleBlue,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Center(
                  child: VyaparIcon(VyaparIcons.store, color: AppColors.blue),
                ),
              ),
              title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text(locality),
              trailing: const Icon(Icons.check_circle, color: AppColors.success),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.paleCyan,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(
                children: [
                  Icon(Icons.volume_up_rounded, color: AppColors.cyan, size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Paytm Soundbox Active • Instant voice payment alerts connected',
                      style: TextStyle(fontSize: 12, color: AppColors.navy),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

void _showCampaignDialog(BuildContext context, {required String title}) {
  showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: const Row(
        children: [
          VyaparIcon(VyaparIcons.megaphone, color: AppColors.blue, size: 22),
          SizedBox(width: 8),
          Text('Launch Campaign', style: TextStyle(fontSize: 17)),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
          ),
          const SizedBox(height: 8),
          const Text(
            'Target: 146 repeat local customers via WhatsApp & SMS broadcast.',
            style: TextStyle(fontSize: 12.5, color: AppColors.muted),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: AppColors.blue),
          onPressed: () {
            Navigator.pop(context);
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Campaign broadcast scheduled successfully!'),
              ),
            );
          },
          child: const Text('Send Broadcast'),
        ),
      ],
    ),
  );
}
