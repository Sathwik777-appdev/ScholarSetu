import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config.dart';
import '../data/api.dart';
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

  static const _demoPersonas = [
    ('Sunita (Student)', '9876543210'),
    ('You (8867494183)', '8867494183'),
    ('Kavita (Mitra)', '9876543220'),
    ('Babulal (Guardian)', '9876543212'),
  ];

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
        final msg = res is Map ? (res['message'] as String?) : null;
        setState(() {
          _codeSent = true;
          _otp.text = '123456';
          _note = msg != null ? '$msg\nDemo code: 123456 (auto-filled).' : 'Demo code: 123456 (auto-filled).';
        });
      });

  Future<void> _verify() => _run(() async {
        final api = ref.read(servicesProvider).api;
        final res = await api.post('/auth/otp/verify', {'phone': _phone.text.trim(), 'otp': _otp.text.trim()});
        await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
      });

  Future<void> _instantDemoSignIn() => _run(() async {
        final api = ref.read(servicesProvider).api;
        final phone = _phone.text.trim().isEmpty ? '9876543210' : _phone.text.trim();
        try {
          final res = await api.post('/auth/otp/verify', {'phone': phone, 'otp': '123456'});
          await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
        } on OfflineException {
          // If server is unreachable, log in with local demo credentials
          await _enterOfflineDemo();
        }
      });

  Future<void> _enterOfflineDemo() async {
    final phone = _phone.text.trim();
    String name = 'Sunita Hansda';
    String role = 'STUDENT';
    String? studentId = 'stu-sunita-001';
    String? householdId = 'hh_hansda_001';

    if (phone == '9876543220') {
      name = 'Kavita Tudu (Hostel Warden)';
      role = 'MITRA';
      studentId = null;
      householdId = null;
    } else if (phone == '9876543212') {
      name = 'Babulal Hansda';
      role = 'GUARDIAN';
      studentId = null;
      householdId = 'hh_hansda_001';
    }

    final demoSession = {
      'access_token': 'demo-token-$phone',
      'token_type': 'bearer',
      'expires_in': 86400,
      'user': {
        'id': '01a0e33d-0307-7c0e-9158-bfffc7bbbf91',
        'name': name,
        'role': role,
        'student_id': studentId,
        'household_id': householdId,
        'jurisdiction_state': 'Jharkhand',
        'jurisdiction_district': 'Dumka',
      }
    };
    await ref.read(sessionProvider.notifier).signIn(demoSession);
  }

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
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.saffron.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.saffron.withValues(alpha: 0.35)),
            ),
            child: Row(
              children: [
                const Icon(Icons.bolt_rounded, color: AppColors.saffron, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text('Demo Mode Active', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.text)),
                      Text('Pick a persona or enter any number. Fixed code is 123456.', style: TextStyle(fontSize: 11, color: AppColors.muted)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const Text('Choose Demo Persona:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.muted)),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: _demoPersonas.map((p) {
              final isSelected = _phone.text.trim() == p.$2;
              return GestureDetector(
                onTap: () {
                  setState(() {
                    _phone.text = p.$2;
                    _codeSent = false;
                    _error = null;
                  });
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: isSelected ? AppColors.ink900 : Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: isSelected ? AppColors.ink900 : AppColors.line),
                  ),
                  child: Text(
                    p.$1,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                      color: isSelected ? Colors.white : AppColors.text,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
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
              decoration: const InputDecoration(
                labelText: 'Code from SMS',
                prefixIcon: Icon(Icons.password_rounded),
                helperText: 'Demo code is 123456',
              ),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: _busy ? null : (_codeSent ? _verify : _sendCode),
                  child: Text(_busy ? 'Please wait…' : (_codeSent ? 'Sign in' : 'Send code')),
                ),
              ),
              if (!_codeSent) ...[
                const SizedBox(width: 10),
                FilledButton.tonalIcon(
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.saffron.withValues(alpha: 0.2),
                    foregroundColor: Colors.brown.shade900,
                  ),
                  onPressed: _busy ? null : _instantDemoSignIn,
                  icon: const Icon(Icons.bolt_rounded, size: 18),
                  label: const Text('1-Tap Demo'),
                ),
              ],
            ],
          ),
          if (_codeSent)
            TextButton(
              onPressed: _busy ? null : () => setState(() => _codeSent = false),
              child: const Text('Use a different number'),
            ),
          if (_error != null) ...[
            ErrorBox(message: _error!),
            const SizedBox(height: 6),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                visualDensity: VisualDensity.compact,
                side: BorderSide(color: AppColors.teal.withValues(alpha: 0.5)),
              ),
              icon: const Icon(Icons.offline_bolt_rounded, size: 18, color: AppColors.teal),
              label: const Text('Enter Offline Demo Mode', style: TextStyle(color: AppColors.teal, fontWeight: FontWeight.w600)),
              onPressed: _enterOfflineDemo,
            ),
          ],
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
