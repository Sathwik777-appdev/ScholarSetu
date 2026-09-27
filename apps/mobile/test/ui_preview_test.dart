// Renders the main visual components with real fonts and 3D-rendered assets. Always checks they build;
// with UI_PREVIEW_DIR set it also saves PNG screenshots for design review.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsetu_mobile/ui/components.dart';
import 'package:scholarsetu_mobile/ui/login_screen.dart';
import 'package:scholarsetu_mobile/ui/student_screens.dart';
import 'package:scholarsetu_mobile/ui/theme.dart';

Future<void> _loadFonts() async {
  final loader = FontLoader('Inter');
  for (final w in ['Regular', 'Medium', 'SemiBold', 'Bold']) {
    loader.addFont(rootBundle.load('assets/fonts/Inter-$w.ttf'));
  }
  await loader.load();
  // Material icons for the preview.
  final icons = FontLoader('MaterialIcons');
  final path = '${Platform.environment['FLUTTER_ROOT'] ?? ''}/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf';
  if (File(path).existsSync()) {
    icons.addFont(Future.value(ByteData.view(File(path).readAsBytesSync().buffer)));
    await icons.load();
  }
}

Future<void> _capture(WidgetTester tester, String name) async {
  final dir = Platform.environment['UI_PREVIEW_DIR'];
  if (dir == null) return;
  await tester.runAsync(() async {
    for (final element in find.byType(Image).evaluate()) {
      final image = element.widget as Image;
      await precacheImage(image.image, element);
    }
  });
  await tester.pumpAndSettle();
  final boundary = tester.renderObject<RenderRepaintBoundary>(find.byKey(const Key('preview')));
  await tester.runAsync(() async {
    final img = await boundary.toImage(pixelRatio: 2);
    final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
    File('$dir/$name.png').writeAsBytesSync(bytes!.buffer.asUint8List());
  });
}

Widget _frame(Widget child) => ProviderScope(
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        home: RepaintBoundary(key: const Key('preview'), child: child),
      ),
    );

void main() {
  setUpAll(_loadFonts);

  testWidgets('login screen', (tester) async {
    tester.view.physicalSize = const Size(390 * 2, 844 * 2);
    tester.view.devicePixelRatio = 2;
    await tester.pumpWidget(_frame(const LoginScreen()));
    expect(find.text('Sign in'), findsOneWidget);
    await _capture(tester, 'login');
  });

  testWidgets('home components', (tester) async {
    tester.view.physicalSize = const Size(390 * 2, 844 * 2);
    tester.view.devicePixelRatio = 2;
    // Illustrative values for the preview only; the app shows what the API returns.
    final apps = [
      {'id': 'APP-PM-2026-000002', 'scheme': 'POST_MATRIC', 'academic_year': '2026-27',
       'current_state': 'AUTHORITY_VERIFICATION', 'next_action': 'The district/state authority is verifying your application'},
      {'id': 'APP-PRM-2025-000001', 'scheme': 'PRE_MATRIC', 'academic_year': '2025-26',
       'current_state': 'CREDITED', 'next_action': ''},
    ];
    await tester.pumpWidget(_frame(Scaffold(
      body: SafeArea(child: ListView(padding: const EdgeInsets.all(16), children: [
        const HeroHeader(title: 'Hello, Sunita', subtitle: 'Here is where your scholarships stand.',
            image: 'assets/images/badge.webp', imageSize: 96,
            trailing: Figure(label: 'Received so far', value: '₹0', color: Colors.white)),
        for (final a in apps) ApplicationCard(application: a),
        const HeroHeader(title: '₹8,000', subtitle: 'credited to your bank, of ₹8,000 sanctioned',
            image: 'assets/images/coins.webp', imageSize: 104),
      ])),
      bottomNavigationBar: NavigationBar(selectedIndex: 0, destinations: const [
        NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Home'),
        NavigationDestination(icon: Icon(Icons.currency_rupee), label: 'Money'),
        NavigationDestination(icon: Icon(Icons.verified_outlined), label: 'Passport'),
        NavigationDestination(icon: Icon(Icons.chat_outlined), label: 'JAGO'),
        NavigationDestination(icon: Icon(Icons.notifications_outlined), label: 'Alerts'),
      ]),
    )));
    expect(find.text('Post-Matric'), findsOneWidget);
    expect(find.byType(StageTracker), findsNWidgets(2));
    await _capture(tester, 'home');
  });
}
