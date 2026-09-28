import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/providers.dart';
import 'server_sheet.dart';
import 'widgets.dart';

/// Registration: the phone is confirmed by an SMS code before any account exists. Registering does NOT
/// apply for a scholarship; the dashboard then shows "Registered — application NOT submitted".
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _phone = TextEditingController();
  final _otp = TextEditingController();
  final _name = TextEditingController();
  final _father = TextEditingController();
  final _state = TextEditingController();
  final _district = TextEditingController();
  DateTime? _dob;
  String _gender = 'FEMALE';
  String _language = 'hi';
  bool _codeSent = false;
  bool _busy = false;
  String? _error;

  Future<void> _sendCode() async {
    if (_phone.text.trim().length != 10) {
      setState(() => _error = 'Enter your 10-digit mobile number.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(servicesProvider).api.post('/auth/register/start', {'phone': _phone.text.trim()});
      setState(() => _codeSent = true);
    } catch (e) {
      setState(() => _error = errorText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _complete() async {
    if (!_form.currentState!.validate()) return;
    if (_dob == null) {
      setState(() => _error = 'Choose your date of birth.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res = await ref.read(servicesProvider).api.post('/auth/register/complete', {
        'phone': _phone.text.trim(),
        'otp': _otp.text.trim(),
        'full_name': _name.text.trim(),
        'dob': _dob!.toIso8601String().substring(0, 10),
        'gender': _gender,
        'state': _state.text.trim(),
        'district': _district.text.trim(),
        if (_father.text.trim().isNotEmpty) 'father_name': _father.text.trim(),
        'preferred_language': _language,
      });
      await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } catch (e) {
      setState(() => _error = errorText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String? _required(String? v) => (v == null || v.trim().length < 2) ? 'Required' : null;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Register'),
        actions: [
          IconButton(
            icon: const Icon(Icons.dns_rounded),
            tooltip: 'Server connection settings',
            onPressed: () => showServerConfigSheet(context, ref),
          ),
        ],
      ),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const Text('Step 1: confirm your mobile number. We send a code by SMS.'),
            const SizedBox(height: 12),
            TextFormField(
              controller: _phone,
              enabled: !_codeSent,
              keyboardType: TextInputType.phone,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(10)],
              decoration: const InputDecoration(labelText: 'Mobile number', border: OutlineInputBorder()),
            ),
            if (!_codeSent) ...[
              const SizedBox(height: 12),
              FilledButton(onPressed: _busy ? null : _sendCode, child: const Text('Send code')),
            ],
            if (_codeSent) ...[
              const SizedBox(height: 12),
              TextFormField(
                controller: _otp,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
                validator: (v) => (v ?? '').length == 6 ? null : 'Enter the 6-digit code',
                decoration: const InputDecoration(labelText: 'Code from SMS', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 20),
              const Text('Step 2: your details, as on your Aadhaar and certificates. They are checked '
                  'with the issuing offices later; nothing here counts as verified.'),
              const SizedBox(height: 12),
              TextFormField(controller: _name, validator: _required,
                  decoration: const InputDecoration(labelText: 'Full name', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () async {
                  final picked = await showDatePicker(context: context, firstDate: DateTime(1970),
                      lastDate: DateTime.now().subtract(const Duration(days: 1)), initialDate: DateTime(2008));
                  if (picked != null) setState(() => _dob = picked);
                },
                child: Text(_dob == null ? 'Date of birth' : 'Born ${_dob!.toIso8601String().substring(0, 10)}'),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _gender,
                decoration: const InputDecoration(labelText: 'Gender', border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(value: 'FEMALE', child: Text('Female')),
                  DropdownMenuItem(value: 'MALE', child: Text('Male')),
                  DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                ],
                onChanged: (v) => setState(() => _gender = v ?? _gender),
              ),
              const SizedBox(height: 12),
              TextFormField(controller: _father,
                  decoration: const InputDecoration(labelText: "Father's name (optional)", border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextFormField(controller: _state, validator: _required,
                  decoration: const InputDecoration(labelText: 'State', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextFormField(controller: _district, validator: _required,
                  decoration: const InputDecoration(labelText: 'District', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _language,
                decoration: const InputDecoration(labelText: 'Language for messages', border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(value: 'hi', child: Text('हिन्दी (Hindi)')),
                  DropdownMenuItem(value: 'en', child: Text('English')),
                ],
                onChanged: (v) => setState(() => _language = v ?? _language),
              ),
              const SizedBox(height: 20),
              FilledButton(onPressed: _busy ? null : _complete, child: Text(_busy ? 'Please wait…' : 'Register')),
            ],
            if (_error != null) ErrorBox(message: _error!),
          ],
        ),
      ),
    );
  }
}
