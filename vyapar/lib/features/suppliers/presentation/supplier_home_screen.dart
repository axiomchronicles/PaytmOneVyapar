import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/layout/sliver_section.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/features/orders/models/order_detail.dart';
import 'package:vyapar/features/suppliers/providers/supplier_provider.dart';

class SupplierHomeScreen extends ConsumerWidget {
  const SupplierHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(authControllerProvider).value;
    final profileAsync = ref.watch(mySupplierProfileProvider);
    final nearbyMerchantsAsync = ref.watch(nearbyMerchantsProvider);
    final ordersAsync = ref.watch(mySupplierOrdersProvider);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        top: true,
        bottom: false,
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(mySupplierProfileProvider);
            ref.invalidate(nearbyMerchantsProvider);
            ref.invalidate(mySupplierOrdersProvider);
          },
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              // Top Bar
              SliverPadding(
                padding: const EdgeInsets.all(AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                session?.businessName.isNotEmpty == true
                                    ? session!.businessName
                                    : 'Supplier Hub',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF002E6E),
                                ),
                              ),
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFE0F2FE),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: const Text(
                                  'SUPPLIER',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                    color: Color(0xFF007AEB),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text(
                            session?.gstin != null
                                ? 'GSTIN: ${session!.gstin}'
                                : 'Verified B2B Partner',
                            style: const TextStyle(
                              fontSize: 12,
                              color: Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                      IconButton(
                        icon: const Icon(
                          Icons.logout,
                          color: Color(0xFF64748B),
                        ),
                        tooltip: 'Sign Out',
                        onPressed: () =>
                            ref.read(authControllerProvider.notifier).signOut(),
                      ),
                    ],
                  ),
                ),
              ),

              // Hero Banner
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF002E6E), Color(0xFF005BAC)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF002E6E).withValues(alpha: 0.2),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Wholesale Order Fulfillment',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Live A2A replenishment orders from local kirana stores.',
                          style: TextStyle(
                            color: Color(0xFFE0F2FE),
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            ElevatedButton.icon(
                              onPressed: () =>
                                  context.push('/suppliers/merchants'),
                              icon: const Icon(Icons.storefront, size: 16),
                              label: const Text('Nearby Kirana Stores'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.white,
                                foregroundColor: const Color(0xFF002E6E),
                                elevation: 0,
                                textStyle: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                ),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                  vertical: 8,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton.icon(
                              key: const Key('manage_supplier_inventory'),
                              onPressed: () =>
                                  context.push('/supplier-home/inventory'),
                              icon: const Icon(
                                Icons.inventory_2_outlined,
                                size: 16,
                              ),
                              label: const Text('My inventory'),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Colors.white,
                                side: const BorderSide(color: Colors.white),
                                textStyle: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                ),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                  vertical: 8,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 16)),

              // KPI Grid
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: Row(
                    children: [
                      Expanded(
                        child: _KpiCard(
                          title: 'Incoming Orders',
                          value: ordersAsync.when(
                            data: (orders) => orders.length.toString(),
                            loading: () => '...',
                            error: (_, _) => '0',
                          ),
                          subtitle: 'From local merchants',
                          icon: Icons.receipt_long,
                          color: const Color(0xFF007AEB),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _KpiCard(
                          title: 'Catalog Items',
                          value: profileAsync.when(
                            data: (p) => p.productCount.toString(),
                            loading: () => '...',
                            error: (_, _) => '0',
                          ),
                          subtitle: 'Available for order',
                          icon: Icons.inventory_2,
                          color: const Color(0xFF00BFA5),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 20)),

              // Section: Incoming Orders
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Incoming Purchase Orders',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF002E6E),
                        ),
                      ),
                      TextButton(
                        onPressed: () =>
                            ref.invalidate(mySupplierOrdersProvider),
                        child: const Text('Refresh'),
                      ),
                    ],
                  ),
                ),
              ),

              ordersAsync.when(
                loading: () => const SliverSection(
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (e, _) =>
                    SliverSection(child: Text('Could not load orders: $e')),
                data: (orders) => orders.isEmpty
                    ? const SliverSection(
                        child: EmptyState(
                          title: 'No incoming orders yet',
                          message:
                              'When nearby retail stores place low-stock replenishment orders, they will appear here.',
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: orders.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final order = orders[index];
                            return SupplierOrderApprovalTile(order: order);
                          },
                        ),
                      ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 20)),

              // Section: Nearby Kirana Stores to Fulfill
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                sliver: SliverToBoxAdapter(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Nearby Kirana Stores',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF002E6E),
                        ),
                      ),
                      TextButton(
                        onPressed: () => context.push('/suppliers/merchants'),
                        child: const Text('Discover More'),
                      ),
                    ],
                  ),
                ),
              ),

              nearbyMerchantsAsync.when(
                loading: () => const SliverSection(
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (e, _) => SliverSection(
                  child: Text('Could not load nearby merchants: $e'),
                ),
                data: (merchants) => merchants.isEmpty
                    ? const SliverSection(
                        child: EmptyState(
                          title: 'No merchants found',
                          message:
                              'No retail stores registered in this area yet.',
                        ),
                      )
                    : SliverPadding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                        ),
                        sliver: SliverList.separated(
                          itemCount: merchants.take(5).length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final m = merchants[index];
                            return Card(
                              elevation: 0,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                                side: const BorderSide(
                                  color: Color(0xFFE2E8F0),
                                ),
                              ),
                              child: ListTile(
                                leading: const CircleAvatar(
                                  backgroundColor: Color(0xFFF1F5F9),
                                  child: Icon(
                                    Icons.store,
                                    color: Color(0xFF475569),
                                  ),
                                ),
                                title: Text(
                                  m.name,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                subtitle: Text(
                                  '${m.city ?? 'Local area'} • ${m.distanceKm != null ? '${m.distanceKm} km away' : 'Nearby'} • ${m.productCount} products',
                                ),
                                trailing: m.phoneNumber != null
                                    ? Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 8,
                                          vertical: 4,
                                        ),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFDCFCE7),
                                          borderRadius: BorderRadius.circular(
                                            6,
                                          ),
                                        ),
                                        child: const Text(
                                          'Connected',
                                          style: TextStyle(
                                            color: Color(0xFF16A34A),
                                            fontSize: 11,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                      )
                                    : null,
                              ),
                            );
                          },
                        ),
                      ),
              ),

              const SliverPadding(padding: EdgeInsets.only(bottom: 32)),
            ],
          ),
        ),
      ),
    );
  }
}

class SupplierOrderApprovalTile extends ConsumerStatefulWidget {
  const SupplierOrderApprovalTile({required this.order, super.key});

  final OrderDetail order;

  @override
  ConsumerState<SupplierOrderApprovalTile> createState() =>
      _SupplierOrderApprovalTileState();
}

class _SupplierOrderApprovalTileState
    extends ConsumerState<SupplierOrderApprovalTile> {
  var _submitting = false;

  Future<void> _decide(bool approved) async {
    setState(() => _submitting = true);
    try {
      await ref
          .read(supplierRepositoryProvider)
          .decideMyOrder(
            orderId: widget.order.id,
            approved: approved,
            idempotencyKey: 'supplier-order-${widget.order.id}-$approved',
          );
      ref.invalidate(mySupplierOrdersProvider);
      ref.invalidate(mySupplierProfileProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            approved
                ? 'Order confirmed and settlement started.'
                : 'Order declined. The merchant has been notified.',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not update this order. Try again.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final order = widget.order;
    final awaitingApproval = order.status == 'APPROVAL_PENDING';
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.sm),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const CircleAvatar(
                backgroundColor: Color(0xFFE0F2FE),
                child: Icon(Icons.shopping_bag, color: Color(0xFF007AEB)),
              ),
              title: Text(
                'Order #${order.id.substring(0, 8)}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              subtitle: Text('Total: ₹${order.totalAmount} · ${order.status}'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push('/order/${order.id}'),
            ),
            if (awaitingApproval) ...[
              const Divider(height: AppSpacing.sm),
              const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.xs),
                child: Text(
                  'Confirm available stock to start settlement.',
                  style: TextStyle(color: Color(0xFF64748B)),
                ),
              ),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      key: Key('reject_supplier_order_${order.id}'),
                      onPressed: _submitting ? null : () => _decide(false),
                      child: const Text('Decline'),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: FilledButton(
                      key: Key('approve_supplier_order_${order.id}'),
                      onPressed: _submitting ? null : () => _decide(true),
                      child: _submitting
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Approve & settle'),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _KpiCard extends StatelessWidget {
  const _KpiCard({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
    required this.color,
  });

  final String title;
  final String value;
  final String subtitle;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: const Color(0xFFE2E8F0)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Color(0xFF64748B),
              ),
            ),
            Icon(icon, size: 18, color: color),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w800,
            color: Color(0xFF1D232C),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          subtitle,
          style: const TextStyle(fontSize: 10.5, color: Color(0xFF94A3B8)),
        ),
      ],
    ),
  );
}
