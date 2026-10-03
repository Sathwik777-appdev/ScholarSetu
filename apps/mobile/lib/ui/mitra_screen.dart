import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n.dart';
import '../state/providers.dart';
import 'home_screen.dart';
import 'labels.dart';
import 'widgets.dart';

/// Mitra (assisted) mode. The helper starts a session for one student and one purpose; the student gets
/// an SMS code and reads it out; only then can the helper act, until the session ends or expires.
/// Nothing about the student is saved on the helper's phone.
class MitraScreen extends ConsumerStatefulWidget {
  const MitraScreen({super.key});

  @override
  ConsumerState<MitraScreen> createState() => _MitraScreenState();
}

class _MitraScreenState extends ConsumerState<MitraScreen> {
  final _studentId = TextEditingController();
  final _otp = TextEditingController(); // always starts empty: the code is on the STUDENT's phone
  String _scope = 'VIEW_STATUS';
  int _minutes = 15;
  Map<String, dynamic>? _session;
  Map<String, dynamic>? _dashboard;
  bool _busy = false;
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

  Future<void> _start() => _run(() async {
        final res = await ref.read(servicesProvider).api.post('/mitra/sessions',
            {'student_id': _studentId.text.trim(), 'scope': _scope, 'duration_minutes': _minutes});
        setState(() => _session = res as Map<String, dynamic>);
      });

  Future<void> _verify() => _run(() async {
        final api = ref.read(servicesProvider).api;
        final res = await api.post('/mitra/sessions/${_session!['session_id']}/verify', {'otp': _otp.text.trim()});
        api.mitraSessionId = res['session_id'] as String;
        setState(() => _session = res as Map<String, dynamic>);
        if (_scope == 'VIEW_STATUS') {
          final dash = await api.get('/me/dashboard');
          setState(() => _dashboard = dash as Map<String, dynamic>);
        }
      });

  Future<void> _end() => _run(() async {
        final api = ref.read(servicesProvider).api;
        final id = _session?['session_id'];
        api.mitraSessionId = null;
        if (id != null) await api.delete('/mitra/sessions/$id');
        setState(() {
          _session = null;
          _dashboard = null;
          _otp.clear();
        });
      });

  @override
  void dispose() {
    ref.read(servicesProvider).api.mitraSessionId = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final status = _session?['status'];
    return Scaffold(
      appBar: AppBar(title: Text(t('Mitra: help a student', 'मित्र: छात्र की मदद करें')), actions: const [AccountMenu()]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_session == null) ...[
          Text(t('Start a session for one student. They will receive a code by SMS and must read it to you.', 'एक छात्र के लिए सत्र शुरू करें। उन्हें SMS से एक कोड मिलेगा और वे आपको पढ़कर बताएँगे।')),
          const SizedBox(height: 12),
          TextField(controller: _studentId,
              decoration: InputDecoration(labelText: t('Student ID', 'छात्र आईडी'), border: const OutlineInputBorder())),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _scope,
            decoration: InputDecoration(labelText: t('What you will do', 'आप क्या करेंगे'), border: const OutlineInputBorder()),
            items: [
              DropdownMenuItem(value: 'VIEW_STATUS', child: Text(t('Check application status', 'आवेदन की स्थिति देखें'))),
              DropdownMenuItem(value: 'UPLOAD_DOCUMENTS', child: Text(t('Upload documents', 'दस्तावेज़ अपलोड करें'))),
              DropdownMenuItem(value: 'RESPOND_DEFICIENCY', child: Text(t('Answer an office query', 'कार्यालय के प्रश्न का उत्तर दें'))),
            ],
            onChanged: (v) => setState(() => _scope = v ?? _scope),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            initialValue: _minutes,
            decoration: InputDecoration(labelText: t('For how long', 'कितनी देर के लिए'), border: const OutlineInputBorder()),
            items: [
              DropdownMenuItem(value: 10, child: Text(t('10 minutes', '10 मिनट'))),
              DropdownMenuItem(value: 15, child: Text(t('15 minutes', '15 मिनट'))),
              DropdownMenuItem(value: 30, child: Text(t('30 minutes', '30 मिनट'))),
            ],
            onChanged: (v) => setState(() => _minutes = v ?? _minutes),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy ? null : _start, child: Text(t('Send code to the student', 'छात्र को कोड भेजें'))),
        ] else if (status == 'PENDING_STUDENT_OTP') ...[
          Text(t('A code was sent to the student ${_session!['student_id']}. Ask them to read it to you.', 'छात्र ${_session!['student_id']} को कोड भेजा गया। उनसे कहें कि वे उसे आपको पढ़कर बताएँ।')),
          const SizedBox(height: 12),
          TextField(
            controller: _otp,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
            decoration: InputDecoration(labelText: t("Code from the student's SMS", 'छात्र के SMS का कोड'), border: const OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy ? null : _verify, child: Text(t('Confirm', 'पुष्टि करें'))),
          TextButton(onPressed: _busy ? null : _end, child: Text(t('Cancel', 'रद्द करें'))),
        ] else ...[
          Card(
            color: Colors.green.shade50,
            child: ListTile(
              title: Text(t('Session active for ${_session!['student_id']} (${humanize(_session!['scope'] as String)})', 'सत्र चालू है: ${_session!['student_id']} (${humanize(_session!['scope'] as String)})')),
              subtitle: Text(t('Ends ${whenIso(_session!['expires_at'] as String?)}. Every action is recorded.', 'समाप्त: ${whenIso(_session!['expires_at'] as String?)}। हर कार्य दर्ज होता है।')),
            ),
          ),
          if (_dashboard != null) ...[
            Section(_dashboard!['student']['name'] as String),
            if ((_dashboard!['applications'] as List).isEmpty) Text(t('Registered — application NOT submitted.', 'पंजीकृत — आवेदन जमा नहीं हुआ।')),
            for (final a in (_dashboard!['applications'] as List).cast<Map<String, dynamic>>())
              ListTile(
                title: Text('${schemeLabel(a['scheme'] as String)} ${a['academic_year']}'),
                subtitle: Text('${stateLabel(a['current_state'] as String)}\n${a['next_action'] ?? ''}'),
                isThreeLine: true,
              ),
          ],
          if (_scope != 'VIEW_STATUS')
            Text(t('Uploading documents and answering queries for a student is not available in this version; '
                'Mitra mode supports status checks.',
                'इस संस्करण में छात्र के लिए दस्तावेज़ अपलोड करना और प्रश्नों का उत्तर देना उपलब्ध नहीं है; '
                'मित्र मोड में केवल स्थिति देखी जा सकती है।')),
          const SizedBox(height: 12),
          FilledButton.tonal(onPressed: _busy ? null : _end, child: Text(t('End session', 'सत्र समाप्त करें'))),
        ],
        if (_error != null) ErrorBox(message: _error!),
      ]),
    );
  }
}
