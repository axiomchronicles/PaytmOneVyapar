import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/design_system/theme/app_theme.dart';
import 'package:vyapar/features/settings/presentation/capabilities_screen.dart';
import 'package:vyapar/features/settings/presentation/channels_screen.dart';
import 'package:vyapar/features/settings/presentation/settings_screen.dart';

Widget _buildTestApp(Widget child) => ProviderScope(
      child: MaterialApp(
        theme: AppTheme.light,
        home: child,
      ),
    );

void main() {
  testWidgets('ChannelsScreen renders Telegram as active and WhatsApp as coming soon', (tester) async {
    await tester.pumpWidget(_buildTestApp(const ChannelsScreen()));
    await tester.pumpAndSettle();

    // Verify Header
    expect(find.text('Communication channels'), findsOneWidget);

    // Verify Telegram Bot
    expect(find.text('Telegram Bot'), findsOneWidget);
    expect(find.text('@PaytmOneVyapar_bot'), findsOneWidget);
    expect(find.text('ACTIVE'), findsWidgets);
    expect(find.text('Copy Bot Link'), findsOneWidget);

    // Verify WhatsApp Business is marked COMING SOON
    expect(find.text('WhatsApp Business'), findsOneWidget);
    expect(find.text('COMING SOON'), findsOneWidget);
    expect(
      find.textContaining('Meta WhatsApp Cloud API integration is currently in development'),
      findsOneWidget,
    );
  });

  testWidgets('SettingsScreen lists Communication channels with Telegram active and WhatsApp coming soon', (tester) async {
    await tester.pumpWidget(_buildTestApp(const SettingsScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Communication channels'), findsOneWidget);
    expect(find.text('Telegram (Active) · WhatsApp (Coming soon)'), findsOneWidget);
  });

  testWidgets('CapabilitiesScreen notes Telegram active and WhatsApp coming soon', (tester) async {
    await tester.pumpWidget(_buildTestApp(const CapabilitiesScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Interactive channels'), findsOneWidget);
    expect(find.textContaining('Telegram channel (@PaytmOneVyapar_bot) is active'), findsOneWidget);
    expect(find.textContaining('WhatsApp channel is coming soon'), findsOneWidget);
  });
}
