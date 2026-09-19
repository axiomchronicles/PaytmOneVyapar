import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/core/auth/auth_session.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/features/suppliers/models/supplier.dart';
import 'package:vyapar/features/suppliers/providers/supplier_provider.dart';

class DiscoveryScreen extends ConsumerStatefulWidget {
  const DiscoveryScreen({super.key, this.isMerchantSearch = false});

  final bool isMerchantSearch;

  @override
  ConsumerState<DiscoveryScreen> createState() => _DiscoveryScreenState();
}

class _DiscoveryScreenState extends ConsumerState<DiscoveryScreen> {
  final _searchController = TextEditingController();
  String _filterCity = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(authControllerProvider).value;
    final isSupplier = session?.isSupplier ?? false;
    final searchingMerchants = widget.isMerchantSearch || isSupplier;

    final suppliersAsync = ref.watch(nearbySuppliersProvider);
    final merchantsAsync = ref.watch(nearbyMerchantsProvider);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: AppHeader(
                title: searchingMerchants
                    ? 'Discover Nearby Kirana Stores'
                    : 'Discover Nearby Suppliers',
                subtitle: searchingMerchants
                    ? 'Find retail merchants to supply grocery & FMCG items'
                    : 'Find verified wholesale distributors & cash & carry hubs',
                leading: IconAction(
                  icon: VyaparIcons.back,
                  label: 'Back',
                  onPressed: context.pop,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              child: TextField(
                controller: _searchController,
                onChanged: (val) => setState(() {}),
                decoration: InputDecoration(
                  hintText: searchingMerchants
                      ? 'Search stores by name, city, or area...'
                      : 'Search suppliers by category, brand, or location...',
                  prefixIcon: const Icon(Icons.search, color: Color(0xFF64748B)),
                  filled: true,
                  fillColor: Colors.white,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: searchingMerchants
                  ? _buildMerchantsList(merchantsAsync)
                  : _buildSuppliersList(suppliersAsync),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuppliersList(AsyncValue<List<NearbySupplier>> asyncValue) {
    return asyncValue.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
      data: (suppliers) {
        final query = _searchController.text.trim().toLowerCase();
        final filtered = suppliers.where((s) {
          if (query.isEmpty) return true;
          return s.name.toLowerCase().contains(query) ||
              (s.city?.toLowerCase().contains(query) ?? false) ||
              (s.category?.toLowerCase().contains(query) ?? false);
        }).toList();

        if (filtered.isEmpty) {
          return const EmptyState(
            title: 'No suppliers found',
            message: 'Try changing search keywords or location.',
          );
        }

        return ListView.separated(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 8),
          itemCount: filtered.length,
          separatorBuilder: (_, _) => const SizedBox(height: 10),
          itemBuilder: (context, index) {
            final s = filtered[index];
            return Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: const Color(0xFFE0F2FE),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.local_shipping, color: Color(0xFF007AEB)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                s.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 14,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                              decoration: BoxDecoration(
                                color: const Color(0xFFDCFCE7),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                '${(s.trustScore * 100).toInt()}% Trust',
                                style: const TextStyle(
                                  color: Color(0xFF16A34A),
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 3),
                        Text(
                          '${s.category ?? 'Wholesale Distributor'} • ${s.city ?? 'Local'}'
                          '${s.distanceKm != null ? ' • ${s.distanceKm} km' : ''}',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${s.productCount} wholesale products in catalog',
                          style: const TextStyle(fontSize: 11, color: Color(0xFF007AEB)),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => context.push('/suppliers/${s.id}'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF002E6E),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                    ),
                    child: const Text('View Deals'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildMerchantsList(AsyncValue<List<NearbyMerchant>> asyncValue) {
    return asyncValue.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
      data: (merchants) {
        final query = _searchController.text.trim().toLowerCase();
        final filtered = merchants.where((m) {
          if (query.isEmpty) return true;
          return m.name.toLowerCase().contains(query) ||
              (m.city?.toLowerCase().contains(query) ?? false);
        }).toList();

        if (filtered.isEmpty) {
          return const EmptyState(
            title: 'No merchants found',
            message: 'No stores match your search keyword.',
          );
        }

        return ListView.separated(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 8),
          itemCount: filtered.length,
          separatorBuilder: (_, _) => const SizedBox(height: 10),
          itemBuilder: (context, index) {
            final m = filtered[index];
            return Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.store, color: Color(0xFF475569)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          m.name,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 3),
                        Text(
                          '${m.city ?? 'Local area'} • ${m.distanceKm != null ? '${m.distanceKm} km away' : 'Nearby'}',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${m.productCount} products in stock • ${m.businessType.toUpperCase()}',
                          style: const TextStyle(fontSize: 11, color: Color(0xFF007AEB)),
                        ),
                      ],
                    ),
                  ),
                  if (m.phoneNumber != null)
                    IconButton(
                      icon: const Icon(Icons.phone, color: Color(0xFF16A34A)),
                      tooltip: 'Call Store',
                      onPressed: () {},
                    ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}
