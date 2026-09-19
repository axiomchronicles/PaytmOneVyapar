import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/inventory/providers/receipt_scan_provider.dart';

class ReceiptScanScreen extends ConsumerWidget {
  const ReceiptScanScreen({super.key});

  Future<void> _scan(
    BuildContext context,
    WidgetRef ref,
    ImageSource source,
  ) async {
    final completed = await ref
        .read(receiptScanControllerProvider.notifier)
        .pickAndScan(source);
    if (completed && context.mounted) {
      await context.push('/inventory/scan-receipt/review');
    }
  }

  bool get _cameraAvailable =>
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.android ||
          defaultTargetPlatform == TargetPlatform.iOS);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(receiptScanControllerProvider);
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.md),
                  child: AppHeader(
                    title: 'Scan receipt',
                    subtitle:
                        'Turn a bill, invoice, or product list into inventory',
                    leading: IconAction(
                      icon: VyaparIcons.back,
                      label: 'Back',
                      onPressed: context.pop,
                    ),
                  ),
                ),
              ),
            ),
            SliverFillRemaining(
              hasScrollBody: false,
              child: AdaptivePadding(
                child: ReceiptScanBody(
                  state: state,
                  cameraAvailable: _cameraAvailable,
                  onCamera: () => _scan(context, ref, ImageSource.camera),
                  onUpload: () => _scan(context, ref, ImageSource.gallery),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ReceiptScanBody extends StatelessWidget {
  const ReceiptScanBody({
    required this.state,
    required this.cameraAvailable,
    required this.onCamera,
    required this.onUpload,
    super.key,
  });

  final ReceiptScanState state;
  final bool cameraAvailable;
  final VoidCallback onCamera;
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xl),
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 180),
        child: state.scanning
            ? ReceiptProcessingState(filename: state.selectedFilename)
            : ReceiptPickerPanel(
                cameraAvailable: cameraAvailable,
                failureMessage: state.failure?.message,
                onCamera: onCamera,
                onUpload: onUpload,
              ),
      ),
    ),
  );
}

class ReceiptProcessingState extends StatelessWidget {
  const ReceiptProcessingState({super.key, this.filename});

  final String? filename;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: 'Processing receipt',
    child: Column(
      key: const ValueKey('receipt_processing'),
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const SizedBox.square(
          dimension: AppSpacing.xxl,
          child: CircularProgressIndicator(strokeWidth: AppSpacing.xxs),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Reading every product…',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          filename ?? 'Your image is being securely processed.',
          textAlign: TextAlign.center,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
        ),
      ],
    ),
  );
}

class ReceiptPickerPanel extends StatelessWidget {
  const ReceiptPickerPanel({
    required this.cameraAvailable,
    required this.onCamera,
    required this.onUpload,
    super.key,
    this.failureMessage,
  });

  final bool cameraAvailable;
  final VoidCallback onCamera;
  final VoidCallback onUpload;
  final String? failureMessage;

  @override
  Widget build(BuildContext context) => Column(
    key: const ValueKey('receipt_picker'),
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      Container(
        width: 104,
        height: 104,
        decoration: const BoxDecoration(
          color: AppColors.paleCyan,
          shape: BoxShape.circle,
        ),
        child: Center(
          child: VyaparIcon(
            VyaparIcons.scan,
            size: AppSpacing.xxl,
            color: AppColors.navy,
          ),
        ),
      ),
      const SizedBox(height: AppSpacing.lg),
      Text(
        'Add stock from a receipt',
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      const SizedBox(height: AppSpacing.xs),
      Text(
        'AI reads what is visible. Missing or uncertain details stay open for your review before anything is saved.',
        textAlign: TextAlign.center,
        style: Theme.of(
          context,
        ).textTheme.bodyLarge?.copyWith(color: AppColors.muted),
      ),
      if (failureMessage case final message?) ...[
        const SizedBox(height: AppSpacing.md),
        ReceiptErrorBanner(message: message),
      ],
      const SizedBox(height: AppSpacing.xl),
      if (cameraAvailable) ...[
        PrimaryButton(
          label: 'Take photo',
          onPressed: onCamera,
          leading: VyaparIcon(VyaparIcons.camera, color: Colors.white),
        ),
        const SizedBox(height: AppSpacing.sm),
      ],
      SecondaryButton(
        label: 'Upload image',
        onPressed: onUpload,
        leading: VyaparIcon(VyaparIcons.imageUpload, color: AppColors.navy),
      ),
      const SizedBox(height: AppSpacing.lg),
      const ReceiptPhotoTips(),
    ],
  );
}

class ReceiptErrorBanner extends StatelessWidget {
  const ReceiptErrorBanner({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: AppColors.dangerSurface,
      borderRadius: BorderRadius.circular(AppRadii.sm),
    ),
    child: Padding(
      padding: const EdgeInsets.all(AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          VyaparIcon(VyaparIcons.warning, color: AppColors.danger),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
            child: Text(
              message,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.danger),
            ),
          ),
        ],
      ),
    ),
  );
}

class ReceiptPhotoTips extends StatelessWidget {
  const ReceiptPhotoTips({super.key});

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadii.md),
      border: Border.all(color: AppColors.outline),
    ),
    child: Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'For the best result',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Keep the full page in frame, use even lighting, and make every line readable. JPEG, PNG, and WebP files up to 10 MB are supported.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
          ),
        ],
      ),
    ),
  );
}
