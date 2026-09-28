import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/api.dart';
import '../state/providers.dart';
import 'theme.dart';
import 'widgets.dart';

/// "Get from DigiLocker": sign in to DigiLocker in the browser, come back, pick issued documents, import them.
/// The server does the OAuth exchange; this screen only opens the sign-in page and polls the session.
class DigiLockerScreen extends ConsumerStatefulWidget {
  const DigiLockerScreen({super.key});

  @override
  ConsumerState<DigiLockerScreen> createState() => _DigiLockerScreenState();
}

class _DigiLockerScreenState extends ConsumerState<DigiLockerScreen> with WidgetsBindingObserver {
  String? _sessionId;
  String? _authorizeUrl;
  String _label = 'DigiLocker';
  bool _testService = false;
  Map<String, dynamic>? _session;
  final _chosen = <String>{};
  String? _error;
  bool _busy = false;
  Timer? _poll;

  Api get _api => ref.read(servicesProvider).repo.api;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _connect();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _refresh(); // back from the browser
  }

  Future<void> _connect() async {
    setState(() {
      _busy = true;
      _error = null;
      _session = null;
      _chosen.clear();
    });
    try {
      final r = await _api.post('/me/digilocker/connect');
      _sessionId = r['session_id'] as String;
      _authorizeUrl = r['authorize_url'] as String;
      _label = r['label'] as String;
      _testService = r['test_service'] == true;
      await _openSignIn();
      _poll?.cancel();
      _poll = Timer.periodic(const Duration(seconds: 3), (_) => _refresh());
    } catch (e) {
      _error = errorText(e);
    }
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _openSignIn() async {
    final ok = await launchUrl(Uri.parse(_authorizeUrl!), mode: LaunchMode.externalApplication);
    if (!ok && mounted) setState(() => _error = 'Could not open the browser for $_label.');
  }

  Future<void> _refresh() async {
    if (_sessionId == null || !mounted) return;
    try {
      final s = await _api.get('/me/digilocker/sessions/$_sessionId') as Map<String, dynamic>;
      if (!mounted) return;
      setState(() => _session = s);
      if (s['status'] != 'PENDING') _poll?.cancel();
    } catch (e) {
      _poll?.cancel();
      if (mounted) setState(() => _error = errorText(e));
    }
  }

  Future<void> _import() async {
    setState(() => _busy = true);
    try {
      final r = await _api.post('/me/digilocker/sessions/$_sessionId/import', {'uris': _chosen.toList()});
      final n = (r['imported'] as List).length;
      ref.invalidate(walletProvider);
      if (!mounted) return;
      showMessage(context, 'Imported $n document${n == 1 ? '' : 's'} from $_label.');
      Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final status = _session?['status'] as String?;
    final docs = ((_session?['documents'] as List?) ?? const []).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: Text('Get from $_label')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (_testService)
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.orange.shade300)),
            child: Text('$_label: a test service. Documents from it are test data, not issuer-signed.',
                style: TextStyle(color: Colors.orange.shade900, fontWeight: FontWeight.w600)),
          ),
        if (_error != null) ErrorBox(message: _error!),
        if (_busy && _session == null) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
        if (_sessionId != null && (status == null || status == 'PENDING')) ...[
          const Text('Sign in to DigiLocker in your browser and allow ScholarSetu to read your documents, '
              'then come back here.'),
          const SizedBox(height: 12),
          OutlinedButton.icon(onPressed: _openSignIn, icon: const Icon(Icons.open_in_browser),
              label: const Text('Open the sign-in page again')),
          const SizedBox(height: 8),
          const Row(children: [
            SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
            SizedBox(width: 10),
            Text('Waiting for DigiLocker…', style: TextStyle(color: AppColors.muted)),
          ]),
        ],
        if (status == 'FAILED') ...[
          Text(_session?['error'] as String? ?? 'The sign-in did not complete.'),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy ? null : _connect, child: const Text('Try again')),
        ],
        if (status == 'CONNECTED') ...[
          Text('Signed in as ${_session?['digilocker_name'] ?? 'you'}. Choose the documents to import:',
              style: Theme.of(context).textTheme.titleSmall),
          if (docs.isEmpty) const Padding(padding: EdgeInsets.only(top: 8), child: Text('No issued documents in DigiLocker.')),
          for (final d in docs)
            CheckboxListTile(
              value: d['already_imported'] == true || _chosen.contains(d['uri']),
              onChanged: d['already_imported'] == true
                  ? null
                  : (v) => setState(() => v == true ? _chosen.add(d['uri'] as String) : _chosen.remove(d['uri'])),
              title: Text(d['name'] as String? ?? d['doctype'] as String? ?? 'Document'),
              subtitle: Text('${d['issuer'] ?? ''}${d['already_imported'] == true ? ' · already in your wallet' : ''}'),
            ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy || _chosen.isEmpty ? null : _import,
              child: Text(_busy ? 'Importing…' : 'Import ${_chosen.length} document${_chosen.length == 1 ? '' : 's'}')),
        ],
      ]),
    );
  }
}
