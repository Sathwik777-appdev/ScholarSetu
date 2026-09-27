import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../state/providers.dart';

class _Message {
  _Message(this.fromUser, this.text, [this.sources = const []]);

  final bool fromUser;
  final String text;
  final List<String> sources;
}

/// JAGO answers from the student's own ledger records and the official guidelines. It needs a connection;
/// offline it says so instead of guessing.
class JagoScreen extends ConsumerStatefulWidget {
  const JagoScreen({super.key});

  @override
  ConsumerState<JagoScreen> createState() => _JagoScreenState();
}

class _JagoScreenState extends ConsumerState<JagoScreen> {
  final _input = TextEditingController();
  final _messages = <_Message>[];
  String _language = 'hi';
  bool _busy = false;

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _messages.add(_Message(true, text));
      _input.clear();
      _busy = true;
    });
    try {
      final res = await ref.read(servicesProvider).api.post('/jago/chat', {'message': text, 'language': _language, 'channel': 'app'});
      final sources = ((res['citations'] as List?) ?? []).map((c) => '${c['source']} — ${c['section']}').toList();
      setState(() => _messages.add(_Message(false, res['response_text'] as String, sources.cast<String>())));
    } on OfflineException {
      setState(() => _messages.add(_Message(false, 'JAGO needs an internet connection. Your question was not sent.')));
    } on ApiException catch (e) {
      setState(() => _messages.add(_Message(false, 'JAGO could not answer: ${e.message}')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(children: [
          const Text('Language:'),
          const SizedBox(width: 8),
          DropdownButton<String>(
            value: _language,
            items: const [
              DropdownMenuItem(value: 'hi', child: Text('हिन्दी')),
              DropdownMenuItem(value: 'en', child: Text('English')),
            ],
            onChanged: (v) => setState(() => _language = v ?? _language),
          ),
        ]),
      ),
      Expanded(
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_messages.isEmpty) const Text('Ask about your application status, your money, or scheme rules.'),
          for (final m in _messages)
            Align(
              alignment: m.fromUser ? Alignment.centerRight : Alignment.centerLeft,
              child: Card(
                color: m.fromUser ? Colors.indigo.shade50 : null,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(m.text),
                    for (final s in m.sources) Text('Source: $s', style: const TextStyle(fontSize: 11)),
                  ]),
                ),
              ),
            ),
        ]),
      ),
      SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Row(children: [
            Expanded(child: TextField(controller: _input, onSubmitted: (_) => _send(),
                decoration: const InputDecoration(hintText: 'Type your question', border: OutlineInputBorder()))),
            IconButton(onPressed: _busy ? null : _send, icon: const Icon(Icons.send)),
          ]),
        ),
      ),
    ]);
  }
}
