import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../data/api.dart';
import '../state/providers.dart';
import 'labels.dart';
import 'theme.dart';
import 'widgets.dart';

Api _api(WidgetRef ref) => ref.read(servicesProvider).repo.api;

// ── Verify my details ───────────────────────────────────────────────────────

/// Shows what verifying an application involves (the claims its rules need and the sources asked about each),
/// takes the student's consent to exactly that list, runs the verification and shows each result.
class VerifyScreen extends ConsumerStatefulWidget {
  const VerifyScreen({super.key, required this.applicationId});

  final String applicationId;

  @override
  ConsumerState<VerifyScreen> createState() => _VerifyScreenState();
}

class _VerifyScreenState extends ConsumerState<VerifyScreen> {
  Map<String, dynamic>? _plan;
  Map<String, dynamic>? _report;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final plan = await _api(ref).get('/applications/${widget.applicationId}/verification-plan');
      if (mounted) setState(() => _plan = plan as Map<String, dynamic>);
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
  }

  Future<void> _verify() async {
    final consent = _plan!['consent'] as Map<String, dynamic>;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final granted = await _api(ref).post('/consents', {
        'requester': consent['requester'],
        'purpose': consent['purpose'],
        'data_items': consent['data_items'],
        'duration_days': consent['duration_days'],
      });
      final report = await _api(ref).post('/verify/claims', {
        'application_id': widget.applicationId,
        'required_claims': consent['data_items'],
        'consent_id': granted['id'],
      });
      ref.invalidate(passportProvider);
      ref.invalidate(pendingActionsProvider);
      if (mounted) setState(() => _report = report as Map<String, dynamic>);
      await _load();
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  static const _statusText = {
    'VERIFIED': 'Verified',
    'PROVISIONAL': 'Found, waiting for an officer to confirm it is you',
    'MANUAL_REVIEW': 'An officer will check this',
    'SOURCE_UNAVAILABLE': 'The government source could not be reached; try again later',
    'NOT_VERIFIED': 'Not verified yet',
  };

  Color _color(String s) => s == 'VERIFIED'
      ? AppColors.teal
      : s == 'SOURCE_UNAVAILABLE'
          ? AppColors.rose
          : s == 'NOT_VERIFIED'
              ? AppColors.muted
              : AppColors.saffron;

  @override
  Widget build(BuildContext context) {
    final claims = ((_plan?['claims'] as List?) ?? const []).cast<Map<String, dynamic>>();
    final results = {
      for (final c in ((_report?['claims'] as List?) ?? const []).cast<Map<String, dynamic>>()) c['claim_type']: c
    };
    final allVerified = claims.isNotEmpty && claims.every((c) => c['status'] == 'VERIFIED');
    return Scaffold(
      appBar: AppBar(title: const Text('Verify my details')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_error != null) ErrorBox(message: _error!, onRetry: _load),
        if (_plan == null && _error == null) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
        if (_plan != null) ...[
          Text('ScholarSetu asks the government offices that issued your records, so you do not have to upload them. '
              'Verified details are reused for every scholarship.',
              style: Theme.of(context).textTheme.bodyMedium),
          const Section('What will be checked'),
          for (final c in claims)
            Card(
              child: ListTile(
                leading: Icon(c['status'] == 'VERIFIED' ? Icons.verified : Icons.radio_button_unchecked,
                    color: _color(results[c['claim_type']]?['status'] as String? ?? c['status'] as String)),
                title: Text(c['label'] as String),
                subtitle: Text([
                  (c['sources'] as List).isEmpty
                      ? 'No online source: an officer checks your document'
                      : 'Asked: ${(c['sources'] as List).join(', ')}',
                  _statusText[results[c['claim_type']]?['status'] ?? c['status']] ?? humanize(c['status'] as String),
                  if (results[c['claim_type']]?['reasons'] is List && (results[c['claim_type']]!['reasons'] as List).isNotEmpty)
                    (results[c['claim_type']]!['reasons'] as List).first as String,
                ].join('\n')),
                isThreeLine: true,
              ),
            ),
          const SizedBox(height: 8),
          if (!allVerified) ...[
            Text('By tapping below you agree that ScholarSetu may ask these offices about the details listed above, '
                'for "${(_plan!['consent'] as Map)['purpose']}", for ${(_plan!['consent'] as Map)['duration_days']} days. '
                'You can withdraw this in Privacy & consent.',
                style: const TextStyle(fontSize: 12.5, color: AppColors.muted)),
            const SizedBox(height: 12),
            FilledButton(onPressed: _busy ? null : _verify, child: Text(_busy ? 'Checking…' : 'Agree and verify')),
          ] else
            const Text('Everything this scholarship needs is verified.'),
        ],
      ]),
    );
  }
}

// ── Payment failed: "my bank is fixed" ──────────────────────────────────────

/// For a failed instalment: what went wrong and how to fix it, then a re-check of the bank account and, if it
/// passes, a new payment request to PFMS.
class BankFixScreen extends ConsumerStatefulWidget {
  const BankFixScreen({super.key, required this.applicationId, required this.paymentId});

  final String applicationId;
  final String paymentId;

  @override
  ConsumerState<BankFixScreen> createState() => _BankFixScreenState();
}

class _BankFixScreenState extends ConsumerState<BankFixScreen> {
  Map<String, dynamic>? _status;
  Map<String, dynamic>? _retry;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await _api(ref).get('/dbt/status/${widget.applicationId}');
      if (mounted) setState(() => _status = s as Map<String, dynamic>);
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
  }

  Future<void> _retryNow() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await _api(ref).post('/dbt/applications/${widget.applicationId}/payments/${widget.paymentId}/retry');
      ref.invalidate(paymentsProvider);
      if (mounted) setState(() => _retry = r as Map<String, dynamic>);
      await _load();
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final payment = ((_status?['payments'] as List?) ?? const [])
        .cast<Map<String, dynamic>>()
        .where((p) => p['payment_id'] == widget.paymentId)
        .firstOrNull;
    final guidance = payment?['guidance'] as Map<String, dynamic>?;
    final hindi = Localizations.localeOf(context).languageCode == 'hi';
    final issues = ((_retry?['issues'] as List?) ?? const []).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: const Text('Fix a failed payment')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_error != null) ErrorBox(message: _error!),
        if (_status == null && _error == null) const Center(child: CircularProgressIndicator()),
        if (payment != null) ...[
          Text('Instalment ${payment['instalment']}: ${rupees(payment['amount'] as num)} · ${humanize(payment['state'] as String)}',
              style: Theme.of(context).textTheme.titleMedium),
          if (guidance != null) ...[
            const SizedBox(height: 8),
            Text((hindi ? guidance['message_hi'] : guidance['message']) as String),
            const Section('How to fix it'),
            for (final (i, step) in ((hindi ? guidance['fix_steps_hi'] : guidance['fix_steps']) as List).indexed)
              ListTile(dense: true, leading: CircleAvatar(radius: 12, child: Text('${i + 1}', style: const TextStyle(fontSize: 12))),
                  title: Text(step as String)),
          ],
          const SizedBox(height: 12),
          if (payment['state'] == 'FAILED')
            FilledButton(
              onPressed: _busy ? null : _retryNow,
              child: Text(_busy ? 'Checking your bank account…' : 'My bank has fixed it: check again and resend'),
            ),
          if (_retry != null && _retry!['status'] == 'SUBMITTED')
            const Padding(padding: EdgeInsets.only(top: 12),
                child: Text('Your bank account passed the check and the payment was requested again. '
                    'You will see it here when PFMS confirms the credit.')),
          if (_retry != null && _retry!['status'] == 'BLOCKED') ...[
            const Padding(padding: EdgeInsets.only(top: 12),
                child: Text('Not resent yet: the bank check still finds a problem.',
                    style: TextStyle(fontWeight: FontWeight.w600))),
            for (final issue in issues) ListTile(dense: true, leading: const Icon(Icons.error_outline),
                title: Text((hindi ? issue['message_hi'] : issue['message']) as String)),
          ],
        ],
      ]),
    );
  }
}

// ── Privacy & consent ───────────────────────────────────────────────────────

/// What the student has agreed to (and can withdraw), a copy of all their data, and requests to erase or
/// correct it.
class PrivacyScreen extends ConsumerStatefulWidget {
  const PrivacyScreen({super.key});

  @override
  ConsumerState<PrivacyScreen> createState() => _PrivacyScreenState();
}

class _PrivacyScreenState extends ConsumerState<PrivacyScreen> {
  List<Map<String, dynamic>>? _consents;
  List<Map<String, dynamic>>? _requests;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await _api(ref).get('/me/consents') as List;
      final r = await _api(ref).get('/me/data-requests') as List;
      if (mounted) {
        setState(() {
          _consents = c.cast<Map<String, dynamic>>();
          _requests = r.cast<Map<String, dynamic>>();
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
  }

  Future<void> _revoke(String id) async {
    try {
      await _api(ref).delete('/consents/$id');
      await _load();
    } catch (e) {
      if (mounted) showMessage(context, errorText(e));
    }
  }

  Future<void> _export() async {
    setState(() => _busy = true);
    try {
      final data = await _api(ref).get('/me/data-export');
      final bytes = Uint8List.fromList(utf8.encode(const JsonEncoder.withIndent('  ').convert(data)));
      final saved = await FilePicker.saveFile(fileName: 'scholarsetu-my-data.json', bytes: bytes,
          mimeType: 'application/json', type: FileType.custom, allowedExtensions: ['json']);
      if (mounted) showMessage(context, saved == null ? 'Not saved.' : 'Your data was saved.');
    } catch (e) {
      if (mounted) showMessage(context, errorText(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _newRequest() async {
    var kind = 'CORRECTION';
    final text = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, setLocal) => AlertDialog(
          title: const Text('Ask about your data'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            RadioGroup<String>(
              groupValue: kind,
              onChanged: (v) => setLocal(() => kind = v ?? kind),
              child: const Column(children: [
                RadioListTile(value: 'CORRECTION', title: Text('Correct something wrong')),
                RadioListTile(value: 'ERASURE', title: Text('Erase my data')),
              ]),
            ),
            TextField(controller: text, maxLines: 3, maxLength: 2000,
                decoration: const InputDecoration(labelText: 'What should change, and why', border: OutlineInputBorder())),
            const Text('Records of money paid to you are kept by law, even after erasure.',
                style: TextStyle(fontSize: 12, color: AppColors.muted)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Send')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    try {
      await _api(ref).post('/me/data-requests', {'kind': kind, 'details': text.text.trim()});
      if (mounted) showMessage(context, 'Sent. An officer will decide and you will see the answer here.');
      await _load();
    } catch (e) {
      if (mounted) showMessage(context, errorText(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final active = (_consents ?? []).where((c) => c['is_active'] == true).toList();
    final past = (_consents ?? []).where((c) => c['is_active'] != true).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Privacy & consent')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_error != null) ErrorBox(message: _error!, onRetry: _load),
          const Section('What you have agreed to'),
          if (_consents != null && active.isEmpty) const Text('Nothing right now.'),
          for (final c in active)
            Card(
              child: ListTile(
                title: Text(c['purpose'] as String),
                subtitle: Text('${humanize(c['requester'] as String)} may read: '
                    '${(c['data_items'] as List).map((i) => humanize('$i')).join(', ')}\n'
                    'Until ${whenIso(c['expires_at'] as String)}'),
                isThreeLine: true,
                trailing: TextButton(onPressed: () => _revoke(c['id'] as String), child: const Text('Withdraw')),
              ),
            ),
          if (past.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 4),
                child: Text('${past.length} earlier agreement(s) withdrawn or expired.', style: const TextStyle(fontSize: 12))),
          const Section('Your data'),
          OutlinedButton.icon(onPressed: _busy ? null : _export, icon: const Icon(Icons.download),
              label: Text(_busy ? 'Preparing…' : 'Download a copy of all my data')),
          const SizedBox(height: 8),
          OutlinedButton.icon(onPressed: _newRequest, icon: const Icon(Icons.edit_note),
              label: const Text('Ask to correct or erase my data')),
          if ((_requests ?? []).isNotEmpty) const Section('Your requests'),
          for (final r in _requests ?? [])
            ListTile(
              leading: Icon(r['status'] == 'OPEN' ? Icons.schedule : r['status'] == 'DONE' ? Icons.check_circle : Icons.cancel),
              title: Text('${humanize(r['kind'] as String)} · ${humanize(r['status'] as String)}'),
              subtitle: Text(r['resolution'] as String? ?? r['details'] as String),
            ),
        ]),
      ),
    );
  }
}

// ── Scholarship Passport QR ─────────────────────────────────────────────────

/// The attestation's signed JWS as a QR code: any verifier can check it offline with ScholarSetu's public key,
/// or online at /v1/attestations/verify-jws.
void showPassportQr(BuildContext context, String claimLabel, String jws) {
  showDialog<void>(
    context: context,
    builder: (c) => AlertDialog(
      title: Text(claimLabel),
      content: SizedBox(
        width: 280,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          QrImageView(data: jws, size: 260, errorCorrectionLevel: QrErrorCorrectLevel.L, backgroundColor: Colors.white),
          const SizedBox(height: 8),
          const Text('Signed by ScholarSetu. An office can scan this to check it, even offline.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 12)),
        ]),
      ),
      actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Close'))],
    ),
  );
}
