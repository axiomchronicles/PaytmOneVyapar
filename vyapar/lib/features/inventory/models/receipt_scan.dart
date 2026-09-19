import 'package:uuid/uuid.dart';
import 'package:vyapar/core/networking/json.dart';

const receiptItemFields = <String>[
  'name',
  'sku',
  'barcode',
  'category',
  'brand',
  'description',
  'quantity',
  'unit',
  'unit_price',
  'purchase_price',
  'selling_price',
  'mrp',
  'gst_rate',
  'tax_amount',
  'discount',
  'total_amount',
  'expiry_date',
  'batch_number',
];

const receiptHeaderFields = <String>[
  'supplier_name',
  'invoice_number',
  'invoice_date',
  'currency',
  'subtotal',
  'tax',
  'total',
];

String? _valueString(Object? value) {
  if (value == null) return null;
  final text = value.toString().trim();
  return text.isEmpty ? null : text;
}

Map<String, double> _confidenceMap(Object? value) {
  if (value is! Map) return const {};
  return {
    for (final entry in value.entries)
      entry.key.toString(): jsonNumber(
        entry.value,
        entry.key.toString(),
      ).toDouble(),
  };
}

enum ReceiptFieldStatus { scanned, uncertain, missing, edited }

class ReceiptMetadata {
  const ReceiptMetadata({
    required this.values,
    required this.fieldConfidence,
    this.editedFields = const {},
    this.sourceText,
  });

  factory ReceiptMetadata.fromJson(JsonMap json) => ReceiptMetadata(
    values: {
      for (final field in receiptHeaderFields) field: _valueString(json[field]),
    },
    fieldConfidence: _confidenceMap(json['field_confidence']),
    editedFields: const {},
    sourceText: jsonOptionalString(json['source_text']),
  );

  final Map<String, String?> values;
  final Map<String, double> fieldConfidence;
  final Set<String> editedFields;
  final String? sourceText;

  String? value(String field) => values[field];

  ReceiptMetadata update(String field, String value) => ReceiptMetadata(
    values: {...values, field: _valueString(value)},
    fieldConfidence: fieldConfidence,
    editedFields: {...editedFields, field},
    sourceText: sourceText,
  );

  ReceiptFieldStatus status(String field) {
    final value = values[field];
    if (value == null || value.isEmpty) return ReceiptFieldStatus.missing;
    if (editedFields.contains(field)) return ReceiptFieldStatus.edited;
    if ((fieldConfidence[field] ?? 0) < 0.75) {
      return ReceiptFieldStatus.uncertain;
    }
    return ReceiptFieldStatus.scanned;
  }

  JsonMap toJson() => {
    ...values,
    'field_confidence': fieldConfidence,
    'source_text': sourceText,
  };
}

class ReceiptReviewItem {
  const ReceiptReviewItem({
    required this.lineId,
    required this.values,
    required this.confidence,
    required this.fieldConfidence,
    required this.missingFields,
    required this.lowConfidenceFields,
    required this.sourceFields,
    required this.editedFields,
    this.sourceText,
    this.matchedProductId,
    this.matchType,
  });

  factory ReceiptReviewItem.fromJson(JsonMap json) => ReceiptReviewItem(
    lineId: jsonString(json['line_id'], 'line_id'),
    values: {
      for (final field in receiptItemFields) field: _valueString(json[field]),
    },
    confidence: jsonNumber(json['confidence'], 'confidence').toDouble(),
    fieldConfidence: _confidenceMap(json['field_confidence']),
    missingFields: jsonList(
      json['missing_fields'],
    ).map((value) => jsonString(value, 'missing_fields')).toSet(),
    lowConfidenceFields: jsonList(
      json['low_confidence_fields'],
    ).map((value) => jsonString(value, 'low_confidence_fields')).toSet(),
    sourceFields: jsonList(
      json['source_fields'],
    ).map((value) => jsonString(value, 'source_fields')).toSet(),
    editedFields: const {},
    sourceText: jsonOptionalString(json['source_text']),
    matchedProductId: jsonOptionalString(json['matched_product_id']),
    matchType: jsonOptionalString(json['match_type']),
  );

  factory ReceiptReviewItem.manual() => ReceiptReviewItem(
    lineId: const Uuid().v4(),
    values: {for (final field in receiptItemFields) field: null},
    confidence: 0,
    fieldConfidence: {for (final field in receiptItemFields) field: 0},
    missingFields: receiptItemFields.toSet(),
    lowConfidenceFields: const {},
    sourceFields: const {},
    editedFields: const {},
  );

  final String lineId;
  final Map<String, String?> values;
  final double confidence;
  final Map<String, double> fieldConfidence;
  final Set<String> missingFields;
  final Set<String> lowConfidenceFields;
  final Set<String> sourceFields;
  final Set<String> editedFields;
  final String? sourceText;
  final String? matchedProductId;
  final String? matchType;

  String? value(String field) => values[field];

  bool get isReady =>
      _hasValue('name') &&
      _hasValue('sku') &&
      _positiveNumber('quantity') &&
      _hasValue('unit');

  ReceiptFieldStatus status(String field) {
    if (!_hasValue(field)) return ReceiptFieldStatus.missing;
    if (editedFields.contains(field)) return ReceiptFieldStatus.edited;
    if (lowConfidenceFields.contains(field) ||
        (fieldConfidence[field] ?? 0) < 0.75) {
      return ReceiptFieldStatus.uncertain;
    }
    return ReceiptFieldStatus.scanned;
  }

  ReceiptReviewItem update(String field, String value) => ReceiptReviewItem(
    lineId: lineId,
    values: {...values, field: _valueString(value)},
    confidence: confidence,
    fieldConfidence: fieldConfidence,
    missingFields: missingFields,
    lowConfidenceFields: lowConfidenceFields,
    sourceFields: sourceFields,
    editedFields: {...editedFields, field},
    sourceText: sourceText,
    matchedProductId: matchedProductId,
    matchType: matchType,
  );

  JsonMap toConfirmJson() => {
    'line_id': lineId,
    ...values,
    'confidence': confidence,
    'field_confidence': fieldConfidence,
    'source_text': sourceText,
    'edited_fields': editedFields.toList(growable: false),
  };

  bool _hasValue(String field) => values[field]?.trim().isNotEmpty ?? false;

  bool _positiveNumber(String field) {
    final number = double.tryParse(values[field] ?? '');
    return number != null && number > 0;
  }
}

class ReceiptScanReview {
  const ReceiptScanReview({
    required this.scanId,
    required this.receipt,
    required this.items,
    required this.detectedItems,
    required this.warnings,
    required this.imagePreprocessed,
  });

  factory ReceiptScanReview.fromJson(JsonMap json) => ReceiptScanReview(
    scanId: jsonString(json['scan_id'], 'scan_id'),
    receipt: ReceiptMetadata.fromJson(jsonMap(json['receipt'])),
    items: jsonList(json['items'])
        .map((value) => ReceiptReviewItem.fromJson(jsonMap(value)))
        .toList(growable: false),
    detectedItems: jsonNumber(json['detected_items'], 'detected_items').toInt(),
    warnings: jsonList(
      json['warnings'],
    ).map((value) => jsonString(value, 'warnings')).toList(growable: false),
    imagePreprocessed: jsonBool(
      json['image_preprocessed'],
      'image_preprocessed',
    ),
  );

  final String scanId;
  final ReceiptMetadata receipt;
  final List<ReceiptReviewItem> items;
  final int detectedItems;
  final List<String> warnings;
  final bool imagePreprocessed;

  ReceiptScanReview copyWith({
    ReceiptMetadata? receipt,
    List<ReceiptReviewItem>? items,
  }) => ReceiptScanReview(
    scanId: scanId,
    receipt: receipt ?? this.receipt,
    items: items ?? this.items,
    detectedItems: detectedItems,
    warnings: warnings,
    imagePreprocessed: imagePreprocessed,
  );
}

class ConfirmedReceiptItem {
  const ConfirmedReceiptItem({
    required this.action,
    required this.name,
    required this.sku,
    required this.quantityAdded,
    required this.quantityOnHand,
    required this.unit,
  });

  factory ConfirmedReceiptItem.fromJson(JsonMap json) => ConfirmedReceiptItem(
    action: jsonString(json['action'], 'action'),
    name: jsonString(json['name'], 'name'),
    sku: jsonString(json['sku'], 'sku'),
    quantityAdded: jsonNumber(
      json['quantity_added'],
      'quantity_added',
    ).toDouble(),
    quantityOnHand: jsonNumber(
      json['quantity_on_hand'],
      'quantity_on_hand',
    ).toDouble(),
    unit: jsonString(json['unit'], 'unit'),
  );

  final String action;
  final String name;
  final String sku;
  final double quantityAdded;
  final double quantityOnHand;
  final String unit;
}

class ReceiptConfirmation {
  const ReceiptConfirmation({
    required this.scanId,
    required this.createdCount,
    required this.updatedCount,
    required this.items,
  });

  factory ReceiptConfirmation.fromJson(JsonMap json) => ReceiptConfirmation(
    scanId: jsonString(json['scan_id'], 'scan_id'),
    createdCount: jsonNumber(json['created_count'], 'created_count').toInt(),
    updatedCount: jsonNumber(json['updated_count'], 'updated_count').toInt(),
    items: jsonList(json['items'])
        .map((value) => ConfirmedReceiptItem.fromJson(jsonMap(value)))
        .toList(growable: false),
  );

  final String scanId;
  final int createdCount;
  final int updatedCount;
  final List<ConfirmedReceiptItem> items;
}
