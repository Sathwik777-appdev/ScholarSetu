import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config.dart';
import '../state/providers.dart';
import 'register_screen.dart';
import 'server_sheet.dart';
import 'theme.dart';
import 'widgets.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _phone = TextEditingController();
  final _otp = TextEditingController();
  bool _codeSent = false;
  bool _busy = false;
  String? _note;
  String? _error;

  // Seeded demo accounts (scripts/seed_demo.py, is_demo=true). The server accepts the demo code only for
  // these, and only when it runs in DEMO_MODE. Shown only in demo builds (--dart-define=DEMO_ACCOUNTS=true).
  static const _demoPersonas = [
    ('Sunita (Student)', '9876543210'),
    ('Rahul (Student)', '9876543211'),
    ('Babulal (Guardian)', '9876543212'),
    ('Kavita (Mitra)', '9876543220'),
  ];

  bool get _isDemoPersona => demoAccounts && _demoPersonas.any((p) => p.$2 == _phone.text.trim());

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (e) {
      setState(() => _error = errorText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendCode() => _run(() async {
        final api = ref.read(servicesProvider).api;
        final res = await api.post('/auth/otp/request', {'phone': _phone.text.trim()});
        setState(() {
          _codeSent = true;
          _note = res is Map ? res['message'] as String? : null;
        });
      });

  Future<void> _verify() => _run(() async {
        final api = ref.read(servicesProvider).api;
        final res = await api.post('/auth/otp/verify', {'phone': _phone.text.trim(), 'otp': _otp.text.trim()});
        await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
      });

  /// Demo builds only: sign a seeded demo account in with the demo code. The server decides.
  Future<void> _demoSignIn(String phone) => _run(() async {
        _phone.text = phone;
        final api = ref.read(servicesProvider).api;
        final res = await api.post('/auth/otp/verify', {'phone': phone, 'otp': demoOtp});
        await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
      });

  String _currentServer() {
    try {
      return formatOrigin(ref.read(servicesProvider).api.baseUrl);
    } catch (_) {
      return formatOrigin(defaultApiOrigin);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surface,
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          Container(color: AppColors.ink900, child: Stack(children: [
            Image.asset('assets/images/hero.webp', height: 300, width: double.infinity, fit: BoxFit.cover,
                semanticLabel: 'A bridge carrying students across'),
            Positioned.fill(child: DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                begin: Alignment.topCenter, end: Alignment.bottomCenter,
                colors: [AppColors.ink900.withValues(alpha: 0), AppColors.ink900])))),
            Positioned(left: 24, right: 24, bottom: 18, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('ScholarSetu', style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: Colors.white)),
              const SizedBox(height: 4),
              Text('Every scholarship, one place. Verify once, reuse everywhere.',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 14)),
            ])),
            Positioned(
              top: 8,
              right: 12,
                child: IconButton(
                  icon: Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.35),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.dns_rounded, color: Colors.white, size: 20),
                  ),
                  tooltip: 'Server connection settings',
                  onPressed: () => showServerConfigSheet(context, ref),
                ),
            ),
          ])),
          Container(
            color: AppColors.ink900,
            child: Container(
            padding: const EdgeInsets.fromLTRB(24, 28, 24, 32),
            decoration: const BoxDecoration(color: AppColors.surface,
                borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Sign in', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          const Text('Students, parents/guardians and registered helpers (Mitra).', style: TextStyle(color: AppColors.muted)),
          if (demoAccounts) ...[
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.saffron.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.saffron.withValues(alpha: 0.35)),
              ),
              child: const Row(children: [
                Icon(Icons.bolt_rounded, color: AppColors.saffron, size: 22),
                SizedBox(width: 10),
                Expanded(child: Text('Demo build: tap a demo account to sign in. Other numbers need their SMS code.',
                    style: TextStyle(fontSize: 12, color: AppColors.text))),
              ]),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                for (final p in _demoPersonas)
                  ActionChip(
                    label: Text(p.$1, style: const TextStyle(fontSize: 12)),
                    onPressed: _busy ? null : () => _demoSignIn(p.$2),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 16),
          TextField(
            controller: _phone,
            enabled: !_codeSent,
            keyboardType: TextInputType.phone,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
            decoration: const InputDecoration(labelText: 'Mobile number', prefixIcon: Icon(Icons.phone_iphone_rounded)),
          ),
          if (_codeSent) ...[
            const SizedBox(height: 12),
            if (_note != null)
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.check_circle_rounded, color: Colors.green.shade700, size: 16),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_note!, style: TextStyle(color: Colors.green.shade900, fontSize: 12))),
                  ],
                ),
              ),
            const SizedBox(height: 8),
            TextField(
              controller: _otp,
              keyboardType: TextInputType.number,
              autofillHints: const [AutofillHints.oneTimeCode],
              inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
              decoration: InputDecoration(
                labelText: 'Code from SMS',
                prefixIcon: const Icon(Icons.password_rounded),
                helperText: _isDemoPersona ? 'Demo account: the code is $demoOtp' : null,
              ),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy ? null : (_codeSent ? _verify : _sendCode),
            child: Text(_busy ? 'Please wait…' : (_codeSent ? 'Sign in' : 'Send code')),
          ),
          if (_codeSent)
            TextButton(
              onPressed: _busy ? null : () => setState(() => _codeSent = false),
              child: const Text('Use a different number'),
            ),
          if (_error != null) ErrorBox(message: _error!),
          const Divider(height: 36),
          OutlinedButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RegisterScreen())),
            child: const Text('New student? Register'),
          ),
          const SizedBox(height: 16),
          Center(
            child: TextButton.icon(
              style: TextButton.styleFrom(
                visualDensity: VisualDensity.compact,
                foregroundColor: AppColors.muted,
              ),
              icon: const Icon(Icons.wifi_tethering_rounded, size: 14),
              label: Text(
                'Server: ${_currentServer()}',
                style: const TextStyle(fontSize: 11),
              ),
              onPressed: () async {
                await showServerConfigSheet(context, ref);
                if (mounted) setState(() {});
              },
            ),
          ),
            ]),
          )),
        ],
      ),
    );
  }
}
