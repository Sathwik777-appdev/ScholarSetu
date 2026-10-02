import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n.dart';
import '../state/providers.dart';
import 'theme.dart';
import 'widgets.dart';

/// The short sign-up after DigiLocker has confirmed a new person. Name, date of birth and gender come from
/// DigiLocker and cannot be edited; the student adds where they study. Signing up never applies for a
/// scholarship.
class SignupScreen extends ConsumerStatefulWidget {
  const SignupScreen({super.key, required this.registrationToken, required this.profile});

  final String registrationToken;
  final Map<String, dynamic> profile;

  @override
  ConsumerState<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends ConsumerState<SignupScreen> {
  final _form = GlobalKey<FormState>();
  final _father = TextEditingController();
  final _tribe = TextEditingController();
  final _stateText = TextEditingController();
  final _districtText = TextEditingController();
  String? _state;
  String? _district;
  bool _busy = false;
  String? _error;
  // States and districts that have a ScholarSetu officer (GET /v1/geo/districts). Empty = type them in.
  Map<String, List<String>> _served = {};

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      try {
        final res = await ref.read(servicesProvider).api.get('/geo/districts');
        final served = {
          for (final s in (res['states'] as List)) s['state'] as String: (s['districts'] as List).cast<String>(),
        };
        if (mounted && served.isNotEmpty) setState(() => _served = served);
      } catch (_) {/* offline: free text */}
    });
  }

  String get _chosenState => _served.isEmpty ? _stateText.text.trim() : (_state ?? '');
  String get _chosenDistrict => _served.isEmpty ? _districtText.text.trim() : (_district ?? '');

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res = await ref.read(servicesProvider).api.post('/auth/digilocker/register', {
        'registration_token': widget.registrationToken,
        'state': _chosenState,
        'district': _chosenDistrict,
        if (_father.text.trim().isNotEmpty) 'father_name': _father.text.trim(),
        if (_tribe.text.trim().isNotEmpty) 'tribe': _tribe.text.trim(),
        'preferred_language': appLanguage.value,
      });
      await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  String? _required(String? v) => (v == null || v.trim().length < 2) ? t('Required', 'ज़रूरी है') : null;

  @override
  Widget build(BuildContext context) {
    final p = widget.profile;
    final gender = {'M': t('Male', 'पुरुष'), 'F': t('Female', 'महिला'), 'T': t('Transgender', 'ट्रांसजेंडर')}[
            '${p['gender'] ?? ''}'.toUpperCase()] ??
        '${p['gender'] ?? '-'}';
    return Scaffold(
      appBar: AppBar(title: Text(t('Create your account', 'अपना खाता बनाएँ'))),
      body: Form(
        key: _form,
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppColors.line)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.verified_rounded, color: AppColors.teal),
                const SizedBox(width: 8),
                Text(t('Confirmed by DigiLocker', 'DigiLocker द्वारा पुष्टि'),
                    style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.teal)),
              ]),
              const SizedBox(height: 12),
              _Fact(t('Name', 'नाम'), '${p['name'] ?? '-'}'),
              _Fact(t('Date of birth', 'जन्मतिथि'), '${p['dob'] ?? '-'}'),
              _Fact(t('Gender', 'लिंग'), gender),
            ]),
          ),
          const SizedBox(height: 22),
          Text(t('Where do you study?', 'आप कहाँ पढ़ते हैं?'), style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(t('Your district\'s officers will see your applications.', 'आपके ज़िले के अधिकारी आपके आवेदन देखेंगे।'),
              style: const TextStyle(color: AppColors.muted)),
          const SizedBox(height: 12),
          if (_served.isNotEmpty) ...[
            DropdownButtonFormField<String>(
              initialValue: _state,
              items: [for (final s in _served.keys) DropdownMenuItem(value: s, child: Text(s))],
              onChanged: (v) => setState(() {
                _state = v;
                _district = null;
              }),
              validator: (v) => v == null ? t('Choose your state', 'अपना राज्य चुनें') : null,
              decoration: InputDecoration(labelText: t('State', 'राज्य'), border: const OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              key: ValueKey(_state),
              initialValue: _district,
              items: [for (final d in _served[_state] ?? const <String>[]) DropdownMenuItem(value: d, child: Text(d))],
              onChanged: (v) => setState(() => _district = v),
              validator: (v) => v == null ? t('Choose your district', 'अपना ज़िला चुनें') : null,
              decoration: InputDecoration(labelText: t('District', 'ज़िला'), border: const OutlineInputBorder()),
            ),
          ] else ...[
            TextFormField(controller: _stateText, validator: _required,
                decoration: InputDecoration(labelText: t('State', 'राज्य'), border: const OutlineInputBorder())),
            const SizedBox(height: 12),
            TextFormField(controller: _districtText, validator: _required,
                decoration: InputDecoration(labelText: t('District', 'ज़िला'), border: const OutlineInputBorder())),
          ],
          const SizedBox(height: 12),
          TextFormField(controller: _father,
              decoration: InputDecoration(labelText: t("Father's name (optional)", 'पिता का नाम (वैकल्पिक)'),
                  border: const OutlineInputBorder())),
          const SizedBox(height: 12),
          TextFormField(controller: _tribe,
              decoration: InputDecoration(labelText: t('Tribe (optional)', 'जनजाति (वैकल्पिक)'), border: const OutlineInputBorder())),
          const SizedBox(height: 16),
          Text(t('Creating an account does not apply for a scholarship. You apply from the Home tab.',
                  'खाता बनाने से छात्रवृत्ति का आवेदन नहीं होता। आवेदन होम टैब से करें।'),
              style: const TextStyle(fontSize: 13, color: AppColors.muted)),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: ErrorBox(message: _error!)),
          const SizedBox(height: 16),
          SizedBox(
            height: 54,
            child: FilledButton(onPressed: _busy ? null : _submit,
                child: Text(_busy ? t('Creating…', 'बना रहे हैं…') : t('Create account', 'खाता बनाएँ'),
                    style: const TextStyle(fontSize: 16))),
          ),
        ]),
      ),
    );
  }
}

class _Fact extends StatelessWidget {
  const _Fact(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [
          SizedBox(width: 110, child: Text(label, style: const TextStyle(color: AppColors.muted))),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );
}
