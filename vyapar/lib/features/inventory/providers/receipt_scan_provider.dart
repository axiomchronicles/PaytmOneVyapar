import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/features/inventory/data/receipt_image_picker.dart';
import 'package:vyapar/features/inventory/models/receipt_scan.dart';
import 'package:vyapar/features/inventory/providers/inventory_provider.dart';

final receiptImagePickerProvider = Provider<ReceiptImagePicker>(
  (ref) => ReceiptImagePicker(),
);

class ReceiptScanState {
  const ReceiptScanState({
    this.review,
    this.confirmation,
    this.failure,
    this.selectedFilename,
    this.scanning = false,
    this.confirming = false,
    this.manual = false,
  });

  final ReceiptScanReview? review;
  final ReceiptConfirmation? confirmation;
  final AppFailure? failure;
  final String? selectedFilename;
  final bool scanning;
  final bool confirming;
  final bool manual;

  ReceiptScanState copyWith({
    ReceiptScanReview? review,
    ReceiptConfirmation? confirmation,
    AppFailure? failure,
    String? selectedFilename,
    bool? scanning,
    bool? confirming,
    bool? manual,
    bool clearFailure = false,
    bool clearConfirmation = false,
    bool clearReview = false,
  }) => ReceiptScanState(
    review: clearReview ? null : review ?? this.review,
    confirmation: clearConfirmation ? null : confirmation ?? this.confirmation,
    failure: clearFailure ? null : failure ?? this.failure,
    selectedFilename: selectedFilename ?? this.selectedFilename,
    scanning: scanning ?? this.scanning,
    confirming: confirming ?? this.confirming,
    manual: manual ?? this.manual,
  );
}

class ReceiptScanController extends Notifier<ReceiptScanState> {
  @override
  ReceiptScanState build() => const ReceiptScanState();

  Future<bool> pickAndScan(ImageSource source) async {
    state = state.copyWith(
      scanning: true,
      clearFailure: true,
      clearConfirmation: true,
      clearReview: true,
      manual: false,
    );
    try {
      final image = await ref.read(receiptImagePickerProvider).pick(source);
      if (image == null) {
        state = state.copyWith(scanning: false);
        return false;
      }
      state = state.copyWith(selectedFilename: image.filename);
      final review = await ref
          .read(inventoryRepositoryProvider)
          .scanReceipt(image);
      state = state.copyWith(review: review, scanning: false);
      return true;
    } catch (error) {
      state = state.copyWith(scanning: false, failure: _failure(error));
      return false;
    }
  }

  void updateItem(String lineId, String field, String value) {
    final review = state.review;
    if (review == null) return;
    state = state.copyWith(
      review: review.copyWith(
        items: [
          for (final item in review.items)
            if (item.lineId == lineId) item.update(field, value) else item,
        ],
      ),
      clearFailure: true,
    );
  }

  void updateReceipt(String field, String value) {
    final review = state.review;
    if (review == null) return;
    state = state.copyWith(
      review: review.copyWith(receipt: review.receipt.update(field, value)),
      clearFailure: true,
    );
  }

  void removeItem(String lineId) {
    final review = state.review;
    if (review == null) return;
    state = state.copyWith(
      review: review.copyWith(
        items: review.items.where((item) => item.lineId != lineId).toList(),
      ),
      clearFailure: true,
    );
  }

  void addItem() {
    final review = state.review;
    if (review == null) return;
    state = state.copyWith(
      review: review.copyWith(
        items: [...review.items, ReceiptReviewItem.manual()],
      ),
      clearFailure: true,
    );
  }

  void startManual() {
    state = ReceiptScanState(
      manual: true,
      review: ReceiptScanReview(
        scanId: const Uuid().v4(),
        receipt: ReceiptMetadata(
          values: {for (final field in receiptHeaderFields) field: null},
          fieldConfidence: {for (final field in receiptHeaderFields) field: 0},
        ),
        items: [ReceiptReviewItem.manual()],
        detectedItems: 0,
        warnings: const [],
        imagePreprocessed: false,
      ),
    );
  }

  Future<bool> confirm(String? storeId) async {
    final review = state.review;
    if (review == null || storeId == null || storeId.isEmpty) {
      state = state.copyWith(
        failure: const AppFailure(
          kind: FailureKind.validation,
          message: 'Select the store that should receive this stock.',
        ),
      );
      return false;
    }
    if (review.items.isEmpty) {
      state = state.copyWith(
        failure: const AppFailure(
          kind: FailureKind.validation,
          message: 'Add at least one product before confirming.',
        ),
      );
      return false;
    }
    if (review.items.any((item) => !item.isReady)) {
      state = state.copyWith(
        failure: const AppFailure(
          kind: FailureKind.validation,
          message:
              'Complete product name, SKU, quantity, and unit for every item.',
        ),
      );
      return false;
    }
    state = state.copyWith(confirming: true, clearFailure: true);
    try {
      final repository = ref.read(inventoryRepositoryProvider);
      final result = state.manual
          ? await repository.confirmManualInventory(
              review: review,
              storeId: storeId,
              idempotencyKey: 'manual-${review.scanId}',
            )
          : await repository.confirmReceipt(
              review: review,
              storeId: storeId,
              idempotencyKey: 'receipt-${review.scanId}',
            );
      state = state.copyWith(confirmation: result, confirming: false);
      ref.invalidate(inventoryControllerProvider);
      return true;
    } catch (error) {
      state = state.copyWith(confirming: false, failure: _failure(error));
      return false;
    }
  }

  void reset() => state = const ReceiptScanState();

  static AppFailure _failure(Object error) => error is AppFailure
      ? error
      : const AppFailure(
          kind: FailureKind.unexpected,
          message: 'The receipt could not be processed. Please try again.',
        );
}

final receiptScanControllerProvider =
    NotifierProvider<ReceiptScanController, ReceiptScanState>(
      ReceiptScanController.new,
    );
