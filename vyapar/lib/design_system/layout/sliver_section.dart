import 'package:flutter/widgets.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';

class SliverSection extends StatelessWidget {
  const SliverSection({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) =>
      SliverToBoxAdapter(child: AdaptivePadding(child: child));
}
