
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart' show WidgetsBinding;

import 'data/secure_store.dart';

/// The app language: 'hi' (Hindi) or 'en' (English). Every screen reads it through [t], and the app rebuilds when
/// it changes (main.dart listens). Hindi is the default unless the phone itself is set to English.
final ValueNotifier<String> appLanguage = ValueNotifier('hi');

bool get isHindi => appLanguage.value == 'hi';

/// One string in both languages, written side by side where it is used.
String t(String en, String hi) => isHindi ? hi : en;

Future<void> loadLanguage(SecureStore store) async {
  final saved = await store.language();
  final device = WidgetsBinding.instance.platformDispatcher.locale.languageCode;
  appLanguage.value = saved ?? (device == 'en' ? 'en' : 'hi');
}

Future<void> setLanguage(SecureStore store, String code) async {
  appLanguage.value = code;
  await store.setLanguage(code);
}
