import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config.dart';
import '../i18n.dart';
import '../state/providers.dart';
import 'components.dart';
import 'family_screen.dart';
import 'jago_screen.dart';
import 'labels.dart';
import 'mitra_screen.dart';
import 'rights_screens.dart';
import 'student_screens.dart';
import 'widgets.dart';

/// Chooses the home for the signed-in role and keeps data fresh by polling (no push notifications).
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> with WidgetsBindingObserver {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Future.microtask(_tick);
    _timer = Timer.periodic(pollInterval, (_) => _tick());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _tick();
  }

  Future<void> _tick() async {
    final user = ref.read(sessionProvider).user;
    if (user == null || user.role == 'MITRA') return; // Mitra views go through an assist session
    final report = await ref.read(outboxProvider.notifier).syncNow();
    if (!mounted) return;
    if (report.sent > 0 || report.received > 0) {
      for (final p in [dashboardProvider, householdProvider, paymentsProvider, pendingActionsProvider,
                       notificationsProvider, walletProvider]) {
        ref.invalidate(p);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(sessionProvider).user!;
    return switch (user.role) {
      'GUARDIAN' => const FamilyScreen(),
      'MITRA' => const MitraScreen(),
      _ => const StudentShell(),
    };
  }
}

class StudentShell extends ConsumerStatefulWidget {
  const StudentShell({super.key});

  @override
  ConsumerState<StudentShell> createState() => _StudentShellState();
}

class _StudentShellState extends ConsumerState<StudentShell> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    const pages = [StudentHomeTab(), MoneyTab(), PassportTab(), JagoScreen(), AlertsTab()];
    return Scaffold(
      appBar: AppBar(title: const Text('ScholarSetu'), actions: const [SyncButton(), AccountMenu()]),
      body: Column(children: [const OfflineBanner(), Expanded(child: pages[_tab])]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home_rounded), label: t('Home', 'होम')),
          NavigationDestination(icon: const Icon(Icons.currency_rupee), label: t('Money', 'पैसा')),
          NavigationDestination(icon: const Icon(Icons.verified_outlined), selectedIcon: const Icon(Icons.verified), label: t('Passport', 'पासपोर्ट')),
          const NavigationDestination(icon: Icon(Icons.chat_outlined), selectedIcon: Icon(Icons.chat), label: 'JAGO'),
          NavigationDestination(icon: const Icon(Icons.notifications_outlined), selectedIcon: const Icon(Icons.notifications), label: t('Alerts', 'सूचनाएँ')),
        ],
      ),
    );
  }
}

class SyncButton extends ConsumerWidget {
  const SyncButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final outbox = ref.watch(outboxProvider);
    final badge = outbox.pending + outbox.refused.length;
    return IconButton(
      tooltip: t('Sync', 'सिंक'),
      onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SyncScreen())),
      icon: Badge(isLabelVisible: badge > 0, label: Text('$badge'), child: const Icon(Icons.sync)),
    );
  }
}

class AccountMenu extends ConsumerWidget {
  const AccountMenu({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PopupMenuButton<String>(
      onSelected: (v) async {
        if (v == 'lang') {
          await setLanguage(ref.read(servicesProvider).secure, isHindi ? 'en' : 'hi');
          return;
        }
        if (v == 'privacy') {
          Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PrivacyScreen()));
          return;
        }
        if (v == 'out') {
          final pending = ref.read(outboxProvider).pending;
          final ok = pending == 0 ||
              await showDialog<bool>(
                    context: context,
                    builder: (c) => AlertDialog(
                      title: Text(t('Sign out?', 'साइन आउट करें?')),
                      content: Text(t('$pending change(s) have not been sent yet and will be deleted from this phone.',
                          '$pending बदलाव अभी भेजे नहीं गए हैं और इस फ़ोन से हट जाएँगे।')),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(t('Cancel', 'रद्द करें'))),
                        TextButton(onPressed: () => Navigator.pop(c, true), child: Text(t('Sign out', 'साइन आउट'))),
                      ],
                    ),
                  ) ==
                  true;
          if (ok) await ref.read(sessionProvider.notifier).signOut();
        }
      },
      itemBuilder: (_) => [
        if (ref.read(sessionProvider).user?.role == 'STUDENT')
          PopupMenuItem(value: 'privacy', child: Text(t('Privacy & consent', 'निजता और सहमति'))),
        PopupMenuItem(value: 'lang', child: Text(isHindi ? 'Switch to English' : 'हिन्दी में देखें')),
        PopupMenuItem(value: 'out', child: Text(t('Sign out', 'साइन आउट'))),
      ],
    );
  }
}

/// Everything waiting on this phone, what was refused and why, and the encryption in use.
class SyncScreen extends ConsumerWidget {
  const SyncScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final outbox = ref.watch(outboxProvider);
    final services = ref.read(servicesProvider);
    return Scaffold(
      appBar: AppBar(title: Text(t('Sync', 'सिंक'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          HeroHeader(
            title: outbox.lastSync == null ? t('Not synced yet', 'अभी सिंक नहीं हुआ') : '${t('Synced', 'सिंक हुआ')} ${when(outbox.lastSync!)}',
            subtitle: t('Information saved on this phone is encrypted (SQLCipher ${services.db.cipherVersion}); '
                'the key is kept in the phone\'s secure storage.',
                'इस फ़ोन पर सहेजी जानकारी एन्क्रिप्टेड है (SQLCipher ${services.db.cipherVersion}); कुंजी फ़ोन के सुरक्षित भंडार में है।'),
            image: 'assets/images/shield.webp',
            imageSize: 96,
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: () async {
              final r = await ref.read(outboxProvider.notifier).syncNow();
              if (context.mounted) {
                showMessage(context, r.offline
                    ? t('No connection. Nothing was sent.', 'कनेक्शन नहीं है। कुछ नहीं भेजा गया।')
                    : t('Sent ${r.sent}, refused ${r.refused}, received ${r.received} update(s).',
                        '${r.sent} भेजे, ${r.refused} अस्वीकार, ${r.received} अपडेट मिले।'));
              }
            },
            icon: const Icon(Icons.sync),
            label: Text(t('Sync now', 'अभी सिंक करें')),
          ),
          Section(t('Waiting to send', 'भेजने के लिए बाकी')),
          if (outbox.pending == 0) Text(t('Nothing is waiting.', 'कुछ बाकी नहीं है।')),
          for (final i in outbox.items.where((i) => i.status == 'PENDING'))
            ListTile(
              leading: const Icon(Icons.schedule),
              title: Text(actionLabel(i.action)),
              subtitle: Text('${t('Saved', 'सहेजा')} ${when(i.createdAt)}. ${t('Not sent yet.', 'अभी भेजा नहीं गया।')}'
                  '${i.lastError == null ? '' : ' ${t('Last try', 'पिछली कोशिश')}: ${i.lastError}'}'),
            ),
          Section(t('Refused by the server', 'सर्वर ने अस्वीकार किया')),
          if (outbox.refused.isEmpty) Text(t('None.', 'कोई नहीं।')),
          for (final i in outbox.refused)
            ListTile(
              leading: Icon(Icons.error_outline, color: Colors.red.shade700),
              title: Text(actionLabel(i.action)),
              subtitle: Text(i.lastError ?? t('Refused', 'अस्वीकृत')),
              trailing: TextButton(
                  onPressed: () => ref.read(outboxProvider.notifier).dismiss(i.key), child: Text(t('Dismiss', 'हटाएँ'))),
            ),
        ],
      ),
    );
  }
}
