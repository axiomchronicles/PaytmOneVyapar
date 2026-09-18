import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_pcm_sound/flutter_pcm_sound.dart';

abstract interface class PcmStreamPlayer {
  Future<void> begin();
  Future<void> append(Uint8List bytes);
  Future<void> finish();
  Future<void> flush();
  Future<void> dispose();
}

class NativePcmStreamPlayer implements PcmStreamPlayer {
  NativePcmStreamPlayer({required this.sampleRate, this.prebufferMs = 300});

  final int sampleRate;
  final int prebufferMs;
  final BytesBuilder _prebuffer = BytesBuilder(copy: false);
  bool _configured = false;
  bool _feeding = false;
  Completer<void>? _drained;

  int get _prebufferBytes => sampleRate * 2 * prebufferMs ~/ 1000;

  Future<void> _setup() async {
    if (_configured) return;
    await FlutterPcmSound.setup(
      sampleRate: sampleRate,
      channelCount: 1,
      iosAudioCategory: IosAudioCategory.playAndRecord,
    );
    await FlutterPcmSound.setFeedThreshold(sampleRate ~/ 3);
    await FlutterPcmSound.setLogLevel(LogLevel.error);
    FlutterPcmSound.setFeedCallback((remainingFrames) {
      if (remainingFrames == 0 && !(_drained?.isCompleted ?? true)) {
        _drained?.complete();
      }
    });
    _configured = true;
  }

  @override
  Future<void> begin() async {
    await flush();
    await _setup();
  }

  @override
  Future<void> append(Uint8List bytes) async {
    await _setup();
    if (!_feeding) {
      _prebuffer.add(bytes);
      if (_prebuffer.length < _prebufferBytes) return;
      _feeding = true;
      await _feed(_prebuffer.takeBytes());
      return;
    }
    await _feed(bytes);
  }

  Future<void> _feed(Uint8List bytes) async {
    if (bytes.lengthInBytes.isOdd) {
      bytes = Uint8List.sublistView(bytes, 0, bytes.lengthInBytes - 1);
    }
    if (bytes.isEmpty) return;
    await FlutterPcmSound.feed(
      PcmArrayInt16(bytes: ByteData.sublistView(bytes)),
    );
  }

  @override
  Future<void> finish() async {
    _drained = Completer<void>();
    final pending = _prebuffer.takeBytes();
    if (pending.isNotEmpty) await _feed(pending);
    _feeding = false;
    if (_configured) {
      await _drained?.future.timeout(
        const Duration(seconds: 30),
        onTimeout: () {},
      );
    }
    _drained = null;
  }

  @override
  Future<void> flush() async {
    _prebuffer.takeBytes();
    _feeding = false;
    if (!(_drained?.isCompleted ?? true)) _drained?.complete();
    _drained = null;
    if (_configured) {
      await FlutterPcmSound.release();
      _configured = false;
    }
  }

  @override
  Future<void> dispose() => flush();
}
