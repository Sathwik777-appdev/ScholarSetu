import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
      appBar: AppBar(title: const Text('Mitra: help a student'), actions: const [AccountMenu()]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_session == null) ...[
          const Text('Start a session for one student. They will receive a code by SMS and must read it to you.'),
          const SizedBox(height: 12),
          TextField(controller: _studentId,
              decoration: const InputDecoration(labelText: 'Student ID', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _scope,
            decoration: const InputDecoration(labelText: 'What you will do', border: OutlineInputBorder()),
            items: const [
              DropdownMenuItem(value: 'VIEW_STATUS', child: Text('Check application status')),
              DropdownMenuItem(value: 'UPLOAD_DOCUMENTS', child: Text('Upload documents')),
              DropdownMenuItem(value: 'RESPOND_DEFICIENCY', child: Text('Answer an office query')),
            ],
            onChanged: (v) => setState(() => _scope = v ?? _scope),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            initialValue: _minutes,
            decoration: const InputDecoration(labelText: 'For how long', border: OutlineInputBorder()),
            items: const [
              DropdownMenuItem(value: 10, child: Text('10 minutes')),
              DropdownMenuItem(value: 15, child: Text('15 minutes')),
              DropdownMenuItem(value: 30, child: Text('30 minutes')),
            ],
            onChanged: (v) => setState(() => _minutes = v ?? _minutes),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy ? null : _start, child: const Text('Send code to the student')),
        ] else if (status == 'PENDING_STUDENT_OTP') ...[
          Text('A code was sent to the student ${_session!['student_id']}. Ask them to read it to you.'),
          const SizedBox(height: 12),
          TextField(
            controller: _otp,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(6)],
            decoration: const InputDecoration(labelText: "Code from the student's SMS", border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy ? null : _verify, child: const Text('Confirm')),
          TextButton(onPressed: _busy ? null : _end, child: const Text('Cancel')),
        ] else ...[
          Card(
            color: Colors.green.shade50,
            child: ListTile(
              title: Text('Session active for ${_session!['student_id']} (${humanize(_session!['scope'] as String)})'),
              subtitle: Text('Ends ${whenIso(_session!['expires_at'] as String?)}. Every action is recorded.'),
            ),
          ),
          if (_dashboard != null) ...[
            Section(_dashboard!['student']['name'] as String),
            if ((_dashboard!['applications'] as List).isEmpty) const Text('Registered — application NOT submitted.'),
            for (final a in (_dashboard!['applications'] as List).cast<Map<String, dynamic>>())
              ListTile(
                title: Text('${schemeLabel(a['scheme'] as String)} ${a['academic_year']}'),
                subtitle: Text('${stateLabel(a['current_state'] as String)}\n${a['next_action'] ?? ''}'),
                isThreeLine: true,
              ),
          ],
          if (_scope != 'VIEW_STATUS')
            const Text('Use the student\'s documents or query screen from here in a later version; '
                'this build supports status checks in Mitra mode.'),
          const SizedBox(height: 12),
          FilledButton.tonal(onPressed: _busy ? null : _end, child: const Text('End session')),
        ],
        if (_error != null) ErrorBox(message: _error!),
      ]),
    );
  }
}
