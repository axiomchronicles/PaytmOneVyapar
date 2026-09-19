import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LanguagePreference extends AsyncNotifier<String> {
  static const _key = 'voice_language_code';

  @override
  Future<String> build() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getString(_key) ?? 'hi-IN';
  }

  Future<void> select(String languageCode) async {
    final previous = state.value ?? 'hi-IN';
    state = AsyncData(languageCode);
    try {
      final preferences = await SharedPreferences.getInstance();
      await preferences.setString(_key, languageCode);
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
      state = AsyncData(previous);
    }
  }
}

final languagePreferenceProvider =
    AsyncNotifierProvider<LanguagePreference, String>(LanguagePreference.new);
