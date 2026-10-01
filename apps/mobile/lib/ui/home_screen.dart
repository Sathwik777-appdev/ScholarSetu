import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config.dart';
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
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.currency_rupee), label: 'Money'),
          NavigationDestination(icon: Icon(Icons.verified_outlined), label: 'Passport'),
          NavigationDestination(icon: Icon(Icons.chat_outlined), label: 'JAGO'),
          NavigationDestination(icon: Icon(Icons.notifications_outlined), label: 'Alerts'),
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
      tooltip: 'Sync',
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
                      title: const Text('Sign out?'),
                      content: Text('$pending change(s) have not been sent yet and will be deleted from this phone.'),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
                        TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Sign out')),
                      ],
                    ),
                  ) ==
                  true;
          if (ok) await ref.read(sessionProvider.notifier).signOut();
        }
      },
      itemBuilder: (_) => [
        if (ref.read(sessionProvider).user?.role == 'STUDENT')
          const PopupMenuItem(value: 'privacy', child: Text('Privacy & consent')),
        const PopupMenuItem(value: 'out', child: Text('Sign out')),
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
      appBar: AppBar(title: const Text('Sync')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          HeroHeader(
            title: outbox.lastSync == null ? 'Not synced yet' : 'Synced ${when(outbox.lastSync!)}',
            subtitle: 'Information saved on this phone is encrypted (SQLCipher ${services.db.cipherVersion}); '
                'the key is kept in the phone\'s secure storage.',
            image: 'assets/images/shield.webp',
            imageSize: 96,
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: () async {
              final r = await ref.read(outboxProvider.notifier).syncNow();
              if (context.mounted) {
                showMessage(context, r.offline
                    ? 'No connection. Nothing was sent.'
                    : 'Sent ${r.sent}, refused ${r.refused}, received ${r.received} update(s).');
              }
            },
            icon: const Icon(Icons.sync),
            label: const Text('Sync now'),
          ),
          const Section('Waiting to send'),
          if (outbox.pending == 0) const Text('Nothing is waiting.'),
          for (final i in outbox.items.where((i) => i.status == 'PENDING'))
            ListTile(
              leading: const Icon(Icons.schedule),
              title: Text(humanize(i.action)),
              subtitle: Text('Saved ${when(i.createdAt)}. Not sent yet.'
                  '${i.lastError == null ? '' : ' Last try: ${i.lastError}'}'),
            ),
          const Section('Refused by the server'),
          if (outbox.refused.isEmpty) const Text('None.'),
          for (final i in outbox.refused)
            ListTile(
              leading: Icon(Icons.error_outline, color: Colors.red.shade700),
              title: Text(humanize(i.action)),
              subtitle: Text(i.lastError ?? 'Refused'),
              trailing: TextButton(
                  onPressed: () => ref.read(outboxProvider.notifier).dismiss(i.key), child: const Text('Dismiss')),
            ),
        ],
      ),
    );
  }
}
