import 'package:flutter/material.dart';
import 'package:vyapar/design_system/tokens/colors.dart';

class PageScaffold extends StatelessWidget {
  const PageScaffold({
    required this.body,
    super.key,
    this.appBar,
    this.floatingActionButton,
    this.backgroundColor = AppColors.background,
  });

  final PreferredSizeWidget? appBar;
  final Widget body;
  final Widget? floatingActionButton;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: backgroundColor,
    appBar: appBar,
    body: SafeArea(top: appBar == null, child: body),
    floatingActionButton: floatingActionButton,
  );
}
