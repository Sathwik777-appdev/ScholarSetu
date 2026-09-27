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
          _note = res['message'] as String?;
        });
      });

  Future<void> _verify() => _run(() async {
        final api = ref.read(servicesProvider).api;
        final res = await api.post('/auth/otp/verify', {'phone': _phone.text.trim(), 'otp': _otp.text.trim()});
        await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
      });

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
              child: SafeArea(
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
          const SizedBox(height: 24),
          TextField(
            controller: _phone,
            enabled: !_codeSent,
            keyboardType: TextInputType.phone,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
            decoration: const InputDecoration(labelText: 'Mobile number', prefixIcon: Icon(Icons.phone_iphone_rounded)),
          ),
          if (_codeSent) ...[
            const SizedBox(height: 12),
            if (_note != null) Text(_note!),
            const SizedBox(height: 8),
            TextField(
              controller: _otp,
              keyboardType: TextInputType.number,
              autofillHints: const [AutofillHints.oneTimeCode],
              inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
              decoration: const InputDecoration(labelText: 'Code from SMS', prefixIcon: Icon(Icons.password_rounded)),
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
          const Divider(height: 40),
          OutlinedButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RegisterScreen())),
            child: const Text('New student? Register'),
          ),
          const SizedBox(height: 16),
          Center(
            child: Builder(builder: (ctx) {
              String serverUrl;
              try {
                serverUrl = formatOrigin(ref.watch(servicesProvider).api.baseUrl);
              } catch (_) {
                serverUrl = formatOrigin(defaultApiOrigin);
              }
              return TextButton.icon(
                style: TextButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  foregroundColor: AppColors.muted,
                ),
                icon: const Icon(Icons.wifi_tethering_rounded, size: 14),
                label: Text(
                  'Server: $serverUrl',
                  style: const TextStyle(fontSize: 11),
                ),
                onPressed: () => showServerConfigSheet(context, ref),
              );
            }),
          ),
            ]),
          )),
        ],
      ),
    );
  }
}
