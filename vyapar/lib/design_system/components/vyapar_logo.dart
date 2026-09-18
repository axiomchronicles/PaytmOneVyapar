import 'package:flutter/widgets.dart';

class VyaparLogo extends StatelessWidget {
  const VyaparLogo({super.key, this.height = 44});

  final double height;

  @override
  Widget build(BuildContext context) => Semantics(
    image: true,
    label: 'Paytm One Vyapar',
    child: Image.asset(
      'assets/logo.png',
      height: height,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.medium,
    ),
  );
}
