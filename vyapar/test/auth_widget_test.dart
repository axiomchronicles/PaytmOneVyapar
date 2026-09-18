import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/core/auth/auth_storage.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/features/auth/data/auth_repository.dart';
import 'package:vyapar/features/auth/presentation/sign_in_screen.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/l10n/app_localizations.dart';

class _RejectingAuthRepository extends AuthRepository {
  _RejectingAuthRepository() : super(Dio(), TokenStore(MemoryAuthStorage()));

  @override
  Future<void> signIn({required String email, required String password}) =>
      throw const AppFailure(
        kind: FailureKind.unauthorized,
        message: 'Invalid email or password',
      );
}

void main() {
  testWidgets('sign-in validates input and displays backend auth failure', (
    tester,
  ) async {
    final storage = MemoryAuthStorage();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authStorageProvider.overrideWithValue(storage),
          tokenStoreProvider.overrideWithValue(TokenStore(storage)),
          authRepositoryProvider.overrideWithValue(_RejectingAuthRepository()),
        ],
        child: const MaterialApp(
          localizationsDelegates: [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: SignInScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('sign_in_button')));
    await tester.pump();
    expect(find.text('Enter a valid email address'), findsOneWidget);

    await tester.enterText(
      find.byType(TextFormField).at(0),
      'merchant@example.com',
    );
    await tester.enterText(find.byType(TextFormField).at(1), 'wrong-password');
    await tester.tap(find.byKey(const ValueKey('sign_in_button')));
    await tester.pumpAndSettle();

    expect(find.text('Invalid email or password'), findsOneWidget);
  });
}
