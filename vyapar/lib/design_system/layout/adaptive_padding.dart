import 'package:flutter/widgets.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';

class AdaptivePadding extends StatelessWidget {
  const AdaptivePadding({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final horizontal = width >= 840
        ? AppSpacing.xxl
        : width >= 600
        ? AppSpacing.xl
        : AppSpacing.md;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: horizontal),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 980),
          child: child,
        ),
      ),
    );
  }
}
