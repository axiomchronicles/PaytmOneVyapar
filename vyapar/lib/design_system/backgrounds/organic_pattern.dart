import 'package:flutter/material.dart';
import 'package:vyapar/design_system/tokens/colors.dart';

class OrganicPattern extends StatelessWidget {
  const OrganicPattern({super.key, this.intensity = 1});

  final double intensity;

  @override
  Widget build(BuildContext context) => IgnorePointer(
    child: CustomPaint(
      painter: _OrganicPatternPainter(intensity),
      size: Size.infinite,
    ),
  );
}

class _OrganicPatternPainter extends CustomPainter {
  const _OrganicPatternPainter(this.intensity);

  final double intensity;

  @override
  void paint(Canvas canvas, Size size) {
    final wash = Paint()
      ..color = AppColors.paleBlue.withValues(alpha: 0.68 * intensity);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(size.width * 0.13, size.height * 0.14),
        width: size.width * 0.68,
        height: size.width * 0.54,
      ),
      wash,
    );
    final line = Paint()
      ..color = AppColors.cyan.withValues(alpha: 0.08 * intensity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    for (var index = 0; index < 4; index++) {
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(size.width * 0.1, size.height * 0.15),
          width: size.width * (0.35 + index * 0.08),
          height: size.width * (0.25 + index * 0.07),
        ),
        line,
      );
    }
    canvas.drawCircle(
      Offset(size.width * 0.92, size.height * 0.86),
      size.width * 0.25,
      wash,
    );
  }

  @override
  bool shouldRepaint(covariant _OrganicPatternPainter oldDelegate) =>
      oldDelegate.intensity != intensity;
}
