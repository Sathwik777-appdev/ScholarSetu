import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'config.dart';
import 'data/api.dart';
import 'data/local_db.dart';
import 'data/secure_store.dart';
import 'i18n.dart';
import 'state/providers.dart';
import 'ui/home_screen.dart';
import 'ui/login_screen.dart';
import 'ui/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final secure = SecureStore();
  await initializeDateFormatting('hi');
  await initializeDateFormatting('en');
  await loadLanguage(secure);
  LocalDb db;
  try {
    db = await LocalDb.open(await secure.databaseKey());
  } catch (e) {
    // Fail closed: without the encrypted store the app does not run (it would otherwise keep
    // personal data in plain files).
    runApp(_FatalApp(e.toString()));
    return;
  }

  final customUrl = await secure.apiUrl();
  final effectiveOrigin = (customUrl != null && customUrl.trim().isNotEmpty)
      ? customUrl.trim()
      : defaultApiOrigin;
  final api = Api(formatBaseUrl(effectiveOrigin));

  runApp(ProviderScope(
    retry: (retryCount, error) => null, // screens show errors; users retry explicitly
    overrides: [
      servicesProvider.overrideWithValue(Services(api, db, secure)),
      currentApiOriginProvider.overrideWith(() => _InitialApiOriginNotifier(effectiveOrigin)),
    ],
    child: const ScholarSetuApp(),
  ));
}

class _InitialApiOriginNotifier extends ApiOriginNotifier {
  _InitialApiOriginNotifier(this._initial);
  final String _initial;
  @override
  String build() => _initial;
}

class ScholarSetuApp extends ConsumerWidget {
  const ScholarSetuApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    ref.watch(connectionProvider);
    // Rebuilt when the language changes, so every screen switches at once.
    return ValueListenableBuilder<String>(
      valueListenable: appLanguage,
      builder: (context, lang, _) => MaterialApp(
        key: ValueKey(lang), // every screen redraws in the new language (text comes from t(), not Localizations)
        title: 'ScholarSetu',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        locale: Locale(lang),
        supportedLocales: const [Locale('hi'), Locale('en')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: session.checking
            ? const Scaffold(body: Center(child: CircularProgressIndicator()))
            : session.user == null
                ? const LoginScreen()
                : const HomeScreen(),
      ),
    );
  }
}

class _FatalApp extends StatelessWidget {
  const _FatalApp(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => MaterialApp(
        home: Scaffold(
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text('ScholarSetu cannot start: $message\n\nNo data has been saved on this phone.'),
            ),
          ),
        ),
      );
}
