import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../state/providers.dart';
import 'theme.dart';

class _Message {
  _Message(this.fromUser, this.text, {this.sources = const [], this.aiPhrased = false, this.verifiedText});

  final bool fromUser;
  final String text;
  final List<String> sources;
  final bool aiPhrased;
  final String? verifiedText; // the answer built only from verified records, shown on request
}

/// JAGO answers from the student's own ledger records and the official guidelines. It needs a connection;
/// offline it says so instead of guessing.
///
/// "AI phrasing" is off by default. When the student turns it on, the question and the verified answer are
/// sent to Google's Gemini to be re-phrased; the server keeps the AI text only if every number, date and
/// application ID in it matches the verified answer, which stays one tap away.
class JagoScreen extends ConsumerStatefulWidget {
  const JagoScreen({super.key});

  @override
  ConsumerState<JagoScreen> createState() => _JagoScreenState();
}

class _JagoScreenState extends ConsumerState<JagoScreen> {
  final _input = TextEditingController();
  final _messages = <_Message>[];
  String _language = 'hi';
  bool _aiAssist = false;
  bool _busy = false;

  static const _quick = {
    'hi': ['मेरी छात्रवृत्ति की स्थिति क्या है?', 'मेरा पैसा कब आएगा?', 'क्या कोई काम बाकी है?'],
    'en': ['What is my scholarship status?', 'When will my money come?', 'Is anything pending from me?'],
  };

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _input.text).trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _messages.add(_Message(true, text));
      if (preset == null) _input.clear();
      _busy = true;
    });
    try {
      final res = await ref.read(servicesProvider).api.post('/jago/chat',
          {'message': text, 'language': _language, 'channel': 'app', 'ai_assist': _aiAssist});
      final sources = ((res['citations'] as List?) ?? []).map((c) => '${c['source']} — ${c['section']}').toList();
      final phrased = res['ai_phrased'] == true;
      setState(() => _messages.add(_Message(false, res['response_text'] as String,
          sources: sources.cast<String>(), aiPhrased: phrased,
          verifiedText: phrased ? res['verified_text'] as String? : null)));
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
        padding: const EdgeInsets.fromLTRB(16, 4, 8, 0),
        child: Row(children: [
          DropdownButton<String>(
            value: _language,
            underline: const SizedBox.shrink(),
            items: const [
              DropdownMenuItem(value: 'hi', child: Text('हिन्दी')),
              DropdownMenuItem(value: 'en', child: Text('English')),
            ],
            onChanged: (v) => setState(() => _language = v ?? _language),
          ),
          const Spacer(),
          const Text('AI phrasing', style: TextStyle(fontSize: 13)),
          Switch(
            value: _aiAssist,
            onChanged: (v) async {
              if (v) {
                final ok = await showDialog<bool>(
                  context: context,
                  builder: (c) => AlertDialog(
                    title: const Text('Use AI phrasing?'),
                    content: const Text(
                        'Your questions and JAGO\'s verified answers will be sent to Google (Gemini) so they can be '
                        're-worded. Amounts, dates and application numbers are always checked against your records, '
                        'and the verified answer stays available. You can turn this off at any time.'),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
                      TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes, turn on')),
                    ],
                  ),
                );
                if (ok != true) return;
              }
              setState(() => _aiAssist = v);
            },
          ),
        ]),
      ),
      Expanded(
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (_messages.isEmpty) ...[
            const Text('Ask about your application status, your money, or scheme rules.',
                style: TextStyle(color: AppColors.muted)),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final q in _quick[_language]!)
                ActionChip(label: Text(q, style: const TextStyle(fontSize: 12.5)), onPressed: _busy ? null : () => _send(q)),
            ]),
          ],
          for (final m in _messages) _Bubble(m),
          if (_busy)
            const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator(minHeight: 2)),
        ]),
      ),
      SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Row(children: [
            Expanded(child: TextField(controller: _input, onSubmitted: (_) => _send(),
                decoration: const InputDecoration(hintText: 'Type your question'))),
            const SizedBox(width: 4),
            IconButton.filled(onPressed: _busy ? null : () => _send(), icon: const Icon(Icons.send_rounded)),
          ]),
        ),
      ),
    ]);
  }
}

class _Bubble extends StatefulWidget {
  const _Bubble(this.m);

  final _Message m;

  @override
  State<_Bubble> createState() => _BubbleState();
}

class _BubbleState extends State<_Bubble> {
  bool _showVerified = false;

  @override
  Widget build(BuildContext context) {
    final m = widget.m;
    return Align(
      alignment: m.fromUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
        child: Card(
          color: m.fromUser ? AppColors.ink900 : Colors.white,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m.text, style: TextStyle(color: m.fromUser ? Colors.white : AppColors.text, height: 1.4)),
              for (final s in m.sources)
                Padding(padding: const EdgeInsets.only(top: 6),
                    child: Text('Source: $s', style: const TextStyle(fontSize: 11, color: AppColors.muted))),
              if (m.aiPhrased) ...[
                const SizedBox(height: 6),
                Row(children: [
                  const Icon(Icons.auto_awesome, size: 13, color: AppColors.muted),
                  const SizedBox(width: 4),
                  const Text('AI-phrased · figures checked', style: TextStyle(fontSize: 11, color: AppColors.muted)),
                  const Spacer(),
                  TextButton(
                    style: TextButton.styleFrom(visualDensity: VisualDensity.compact, padding: EdgeInsets.zero),
                    onPressed: () => setState(() => _showVerified = !_showVerified),
                    child: Text(_showVerified ? 'Hide' : 'Verified answer', style: const TextStyle(fontSize: 11)),
                  ),
                ]),
                if (_showVerified && m.verifiedText != null)
                  Container(
                    margin: const EdgeInsets.only(top: 4),
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(10)),
                    child: Text(m.verifiedText!, style: const TextStyle(fontSize: 12.5, height: 1.4)),
                  ),
              ],
            ]),
          ),
        ),
      ),
    );
  }
}
