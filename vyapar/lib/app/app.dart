import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/lifecycle.dart';
import 'package:vyapar/app/router.dart';
import 'package:vyapar/design_system/theme/app_theme.dart';
import 'package:vyapar/l10n/app_localizations.dart';

class VyaparApp extends ConsumerWidget {
  const VyaparApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'Paytm One Vyapar',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: router,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      builder: (context, child) =>
          AppLifecycle(child: child ?? const SizedBox.shrink()),
    );
  }
}
