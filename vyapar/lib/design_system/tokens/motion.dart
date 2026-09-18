import 'package:flutter/animation.dart';

abstract final class AppMotion {
  static const instant = Duration(milliseconds: 120);
  static const micro = Duration(milliseconds: 190);
  static const standard = Duration(milliseconds: 260);
  static const emphasis = Duration(milliseconds: 380);
  static const curve = Curves.easeOutCubic;
}
