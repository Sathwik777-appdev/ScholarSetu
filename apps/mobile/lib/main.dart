import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'config.dart';
import 'data/api.dart';
import 'data/local_db.dart';
import 'data/secure_store.dart';
import 'state/providers.dart';
import 'ui/home_screen.dart';
import 'ui/login_screen.dart';
import 'ui/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final secure = SecureStore();
  LocalDb db;
  try {
    db = await LocalDb.open(await secure.databaseKey());
  } catch (e) {
    // Fail closed: without the encrypted store the app does not run (it would otherwise keep
    // personal data in plain files).
    runApp(_FatalApp(e.toString()));
    return;
  }
  runApp(ProviderScope(
    retry: (retryCount, error) => null, // screens show errors; users retry explicitly
    overrides: [servicesProvider.overrideWithValue(Services(Api(apiBaseUrl), db, secure))],
    child: const ScholarSetuApp(),
  ));
}

class ScholarSetuApp extends ConsumerWidget {
  const ScholarSetuApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    ref.watch(connectionProvider);
    return MaterialApp(
      title: 'ScholarSetu',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: session.checking
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : session.user == null
              ? const LoginScreen()
              : const HomeScreen(),
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
