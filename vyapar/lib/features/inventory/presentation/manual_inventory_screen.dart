import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/features/inventory/presentation/receipt_review_screen.dart';
import 'package:vyapar/features/inventory/providers/receipt_scan_provider.dart';

class ManualInventoryScreen extends ConsumerStatefulWidget {
  const ManualInventoryScreen({super.key});

  @override
  ConsumerState<ManualInventoryScreen> createState() =>
      _ManualInventoryScreenState();
}

class _ManualInventoryScreenState extends ConsumerState<ManualInventoryScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        ref.read(receiptScanControllerProvider.notifier).startManual();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(receiptScanControllerProvider);
    if (!state.manual || state.review == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return const ReceiptReviewScreen();
  }
}
