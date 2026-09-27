import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/providers.dart';
import 'register_screen.dart';
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
      appBar: AppBar(title: const Text('ScholarSetu')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text('Sign in with your mobile number', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 4),
          const Text('For students, parents/guardians and registered helpers (Mitra).'),
          const SizedBox(height: 24),
          TextField(
            controller: _phone,
            enabled: !_codeSent,
            keyboardType: TextInputType.phone,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
            decoration: const InputDecoration(labelText: 'Mobile number', border: OutlineInputBorder()),
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
              decoration: const InputDecoration(labelText: 'Code from SMS', border: OutlineInputBorder()),
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
        ],
      ),
    );
  }
}
