import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config.dart';
import '../data/digilocker_service.dart';
import '../i18n.dart';
import '../state/providers.dart';
import 'register_screen.dart';
import 'server_sheet.dart';
import 'theme.dart';
import 'widgets.dart';

/// Sign in. Real students use DigiLocker, which also creates a new student's account. With the demo toggle on,
/// the demo accounts (Sunita, a student; Babulal, her father) sign in with the demo code; the server accepts that
/// code for demo accounts only.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  bool _busy = false;
  bool _demo = false;
  String? _error;
  Map<String, dynamic>? _demoInfo;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      try {
        final services = ref.read(servicesProvider);
        final on = await services.secure.demoMode();
        if (mounted) setState(() => _demo = on);
        final info = await services.api.get('/auth/demo') as Map<String, dynamic>;
        if (mounted) setState(() => _demoInfo = info);
      } catch (_) {/* offline (or a preview without services): the toggle still shows; signing in reports problems */}
    });
  }

  String _server() {
    try {
      return formatOrigin(ref.read(servicesProvider).api.baseUrl);
    } catch (_) {
      return formatOrigin(defaultApiOrigin);
    }
  }

  Future<void> _setDemo(bool on) async {
    setState(() {
      _demo = on;
      _error = null;
    });
    await ref.read(servicesProvider).secure.setDemoMode(on);
  }

  Future<void> _digilocker() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await DigiLockerSignIn(ref.read(servicesProvider).api).run();
      switch (result) {
        case DigiLockerSignedIn(:final auth):
          await ref.read(sessionProvider.notifier).signIn(auth);
        case DigiLockerNeedsSignup(:final registrationToken, :final profile):
          if (mounted) {
            await Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => SignupScreen(registrationToken: registrationToken, profile: profile)));
          }
        case DigiLockerCancelled():
          break;
      }
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _demoSignIn(Map<String, dynamic> account) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final api = ref.read(servicesProvider).api;
    try {
      final isEmail = account.containsKey('email') && account['email'] != null;
      final payload = isEmail ? {'email': account['email'], 'demo': true} : {'phone': account['phone'], 'demo': true};
      
      await api.post('/auth/otp/request', payload);
      
      final verifyPayload = isEmail 
          ? {'email': account['email'], 'otp': _demoInfo?['demo_code'] ?? '123456', 'demo': true}
          : {'phone': account['phone'], 'otp': _demoInfo?['demo_code'] ?? '123456', 'demo': true};
          
      final res = await api.post('/auth/otp/verify', verifyPayload);
      await ref.read(sessionProvider.notifier).signIn(res as Map<String, dynamic>);
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final accounts = ((_demoInfo?['app_accounts'] as List?) ?? const []).cast<Map<String, dynamic>>().toList();
    if (_demoInfo != null) {
      // Inject Super Admin demo account for Verifier UI
      accounts.add({
        'name': 'Super Admin',
        'role': 'MINISTRY',
        'email': 'kotianchethan4@gmail.com'
      });
    }
    final demoAvailable = _demoInfo?['available'] == true;
    return Scaffold(
      backgroundColor: AppColors.surface,
      body: ListView(padding: EdgeInsets.zero, children: [
        _Hero(onLanguage: (code) => setLanguage(ref.read(servicesProvider).secure, code)),
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              Expanded(child: Text(t('Sign in', 'साइन इन करें'), style: Theme.of(context).textTheme.headlineSmall)),
              _DemoSwitch(value: _demo, onChanged: _busy ? null : _setDemo),
            ]),
            const SizedBox(height: 6),
            Text(
              _demo
                  ? t('Demo mode: try ScholarSetu with sample accounts. Nothing here is real.',
                      'डेमो मोड: नमूना खातों से ScholarSetu आज़माएँ। यहाँ कुछ भी असली नहीं है।')
                  : t('Use DigiLocker to sign in or create your account. Your name and date of birth come from DigiLocker.',
                      'साइन इन करने या खाता बनाने के लिए DigiLocker का उपयोग करें। आपका नाम और जन्मतिथि DigiLocker से आते हैं।'),
              style: const TextStyle(color: AppColors.muted, fontSize: 15, height: 1.4),
            ),
            const SizedBox(height: 20),
            if (!_demo) ...[
              _DigiLockerButton(busy: _busy, onPressed: _digilocker),
              const SizedBox(height: 14),
              Row(children: [
                const Icon(Icons.lock_outline_rounded, size: 16, color: AppColors.muted),
                const SizedBox(width: 6),
                Expanded(child: Text(
                    t('ScholarSetu never sees your DigiLocker password.', 'ScholarSetu आपका DigiLocker पासवर्ड कभी नहीं देखता।'),
                    style: const TextStyle(fontSize: 13, color: AppColors.muted))),
              ]),
            ] else if (_demoInfo != null && !demoAvailable)
              _Notice(t('Demo sign-in is switched off on this server. Turn demo mode off to use DigiLocker.',
                  'इस सर्वर पर डेमो साइन-इन बंद है। DigiLocker इस्तेमाल करने के लिए डेमो मोड बंद करें।'))
            else
              for (final a in accounts)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _DemoAccountCard(account: a, busy: _busy, onTap: () => _demoSignIn(a)),
                ),
            if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: ErrorBox(message: _error!)),
            const SizedBox(height: 28),
            Center(
              child: TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: AppColors.muted),
                icon: const Icon(Icons.dns_outlined, size: 16),
                label: Text('${t('Server', 'सर्वर')}: ${_server()}', style: const TextStyle(fontSize: 12)),
                onPressed: () async {
                  await showServerConfigSheet(context, ref);
                  if (mounted) setState(() {});
                },
              ),
            ),
          ]),
        ),
      ]),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.onLanguage});
  final ValueChanged<String> onLanguage;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.ink900,
      child: Stack(children: [
        Image.asset('assets/images/hero.webp', height: 300, width: double.infinity, fit: BoxFit.cover,
            semanticLabel: t('A bridge carrying students across', 'विद्यार्थियों को पार ले जाता एक पुल')),
        Positioned.fill(child: DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
            begin: Alignment.topCenter, end: Alignment.bottomCenter,
            colors: [AppColors.ink900.withValues(alpha: 0.15), AppColors.ink900.withValues(alpha: 0.95)])))),
        Positioned(
          top: MediaQuery.of(context).padding.top + 12, right: 16,
          child: _LanguageSwitch(onChanged: onLanguage),
        ),
        Positioned(
          left: 24, right: 24, bottom: 22,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Image.asset('assets/images/app_icon.png', width: 44, height: 44, fit: BoxFit.cover),
              ),
              const SizedBox(width: 10),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('ScholarSetu', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700)),
                Text(t('Ministry of Tribal Affairs', 'जनजातीय कार्य मंत्रालय'),
                    style: const TextStyle(color: Colors.white70, fontSize: 12.5)),
              ]),
            ]),
            const SizedBox(height: 14),
            Text(t('Every scholarship, one place.', 'हर छात्रवृत्ति, एक जगह।'),
                style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w700, height: 1.15)),
            const SizedBox(height: 4),
            Text(t('Verify once, reuse everywhere.', 'एक बार सत्यापन, हर जगह उपयोग।'),
                style: const TextStyle(color: Colors.white70, fontSize: 15)),
          ]),
        ),
      ]),
    );
  }
}

class _LanguageSwitch extends StatelessWidget {
  const _LanguageSwitch({required this.onChanged});
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    Widget chip(String code, String label) {
      final selected = appLanguage.value == code;
      return Semantics(
        button: true, selected: selected, label: label,
        child: InkWell(
          borderRadius: BorderRadius.circular(99),
          onTap: () => onChanged(code),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(color: selected ? Colors.white : Colors.transparent, borderRadius: BorderRadius.circular(99)),
            child: Text(label, style: TextStyle(color: selected ? AppColors.ink900 : Colors.white, fontWeight: FontWeight.w600, fontSize: 14)),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(99)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [chip('hi', 'हिन्दी'), chip('en', 'English')]),
    );
  }
}

class _DemoSwitch extends StatelessWidget {
  const _DemoSwitch({required this.value, required this.onChanged});
  final bool value;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      toggled: value,
      label: t('Demo mode', 'डेमो मोड'),
      child: InkWell(
        borderRadius: BorderRadius.circular(99),
        onTap: onChanged == null ? null : () => onChanged!(!value),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 4, 4, 4),
          decoration: BoxDecoration(
            color: value ? AppColors.saffron.withValues(alpha: 0.12) : Colors.white,
            borderRadius: BorderRadius.circular(99),
            border: Border.all(color: value ? AppColors.saffron : AppColors.line),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Text(t('Demo', 'डेमो'), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            const SizedBox(width: 4),
            Switch(value: value, onChanged: onChanged, activeTrackColor: AppColors.saffron,
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap),
          ]),
        ),
      ),
    );
  }
}

class _DigiLockerButton extends StatelessWidget {
  const _DigiLockerButton({required this.busy, required this.onPressed});
  final bool busy;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 58,
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.ink900,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        onPressed: busy ? null : onPressed,
        child: busy
            ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
            : Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
                  child: Image.asset('assets/images/digilocker_logo.png', height: 22, semanticLabel: 'DigiLocker'),
                ),
                const SizedBox(width: 12),
                Text(t('Continue with DigiLocker', 'DigiLocker से आगे बढ़ें'),
                    style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w600)),
              ]),
      ),
    );
  }
}

class _DemoAccountCard extends StatelessWidget {
  const _DemoAccountCard({required this.account, required this.busy, required this.onTap});
  final Map<String, dynamic> account;
  final bool busy;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final guardian = account['role'] == 'GUARDIAN';
    final ministry = account['role'] == 'MINISTRY';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: busy ? null : onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), border: Border.all(color: AppColors.line)),
          child: Row(children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: ministry ? AppColors.ink900.withValues(alpha: 0.1) : (guardian ? AppColors.teal.withValues(alpha: 0.14) : AppColors.saffron.withValues(alpha: 0.16)),
              child: Icon(ministry ? Icons.admin_panel_settings_rounded : (guardian ? Icons.family_restroom_rounded : Icons.school_rounded),
                  color: ministry ? AppColors.ink900 : (guardian ? AppColors.teal : AppColors.saffron)),
            ),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(account['name'] as String, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
              const SizedBox(height: 2),
              Text(ministry ? t('Super Admin · Verify Student Documents', 'सुपर एडमिन · छात्र दस्तावेजों को सत्यापित करें')
                            : (guardian ? t('Parent · sees the whole family', 'अभिभावक · पूरा परिवार देखें')
                            : t('Student · Post-Matric application', 'विद्यार्थी · पोस्ट-मैट्रिक आवेदन')),
                  style: const TextStyle(fontSize: 13.5, color: AppColors.muted)),
            ])),
            const Icon(Icons.arrow_forward_rounded, color: AppColors.muted),
          ]),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.amber.shade50, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.amber.shade200)),
        child: Text(text, style: TextStyle(color: Colors.brown.shade800)),
      );
}
