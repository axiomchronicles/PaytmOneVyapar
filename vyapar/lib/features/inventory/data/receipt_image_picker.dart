import 'dart:typed_data';

import 'package:image_picker/image_picker.dart';

class ReceiptImageInput {
  const ReceiptImageInput({
    required this.bytes,
    required this.filename,
    required this.contentType,
  });

  final Uint8List bytes;
  final String filename;
  final String contentType;
}

class ReceiptImagePicker {
  ReceiptImagePicker({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  Future<ReceiptImageInput?> pick(ImageSource source) async {
    final file = await _picker.pickImage(
      source: source,
      requestFullMetadata: false,
    );
    if (file == null) return null;
    return ReceiptImageInput(
      bytes: await file.readAsBytes(),
      filename: file.name,
      contentType: file.mimeType ?? _contentTypeFor(file.name),
    );
  }

  static String _contentTypeFor(String filename) {
    final lower = filename.toLowerCase();
    if (lower.endsWith('.png')) return 'image/png';
    if (lower.endsWith('.webp')) return 'image/webp';
    return 'image/jpeg';
  }
}
