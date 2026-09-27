import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import '../config.dart';
import '../state/providers.dart';
import 'theme.dart';

Future<void> showServerConfigSheet(BuildContext context, WidgetRef ref) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) => _ServerConfigSheet(ref: ref),
  );
}

class _ServerConfigSheet extends StatefulWidget {
  const _ServerConfigSheet({required this.ref});

  final WidgetRef ref;

  @override
  State<_ServerConfigSheet> createState() => _ServerConfigSheetState();
}

class _ServerConfigSheetState extends State<_ServerConfigSheet> {
  late final TextEditingController _urlCtrl;
  bool _testing = false;
  String? _testSuccess;
  String? _testError;

  static const _presets = [
    ('Cloud Run (Online)', 'https://scholarsetu-api-906769842576.asia-south1.run.app'),
    ('Mac Wi-Fi', 'http://10.138.163.185:8000'),
    ('ADB USB', 'http://localhost:8000'),
    ('Emulator', 'http://10.0.2.2:8000'),
  ];

  @override
  void initState() {
    super.initState();
    final currentBase = widget.ref.read(servicesProvider).api.baseUrl;
    _urlCtrl = TextEditingController(text: formatOrigin(currentBase));
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    final candidate = _urlCtrl.text.trim();
    if (candidate.isEmpty) return;

    setState(() {
      _testing = true;
      _testSuccess = null;
      _testError = null;
    });

    final testOrigin = formatOrigin(candidate);
    try {
      final res = await http
          .get(Uri.parse('$testOrigin/health'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final body = jsonDecode(res.body);
        final service = body['service'] ?? 'ScholarSetu';
        final ver = body['version'] ?? '1.0';
        setState(() {
          _testSuccess = 'Connected! $service (v$ver) is responding.';
        });
      } else {
        setState(() {
          _testError = 'Server returned HTTP ${res.statusCode}.';
        });
      }
    } catch (e) {
      setState(() {
        _testError = 'Could not reach server: $e\n\nTips:\n'
            '• Check that phone and Mac are on the same Wi-Fi.\n'
            '• If using USB cable, run: adb reverse tcp:8000 tcp:8000 and use http://localhost:8000.';
      });
    } finally {
      if (mounted) setState(() => _testing = false);
    }
  }

  Future<void> _save() async {
    final raw = _urlCtrl.text.trim();
    if (raw.isEmpty) return;
    final clean = formatOrigin(raw);
    widget.ref.read(currentApiOriginProvider.notifier).setOrigin(clean);
    await widget.ref.read(servicesProvider).updateApiUrl(clean);
    if (!mounted) return;
    Navigator.of(context).pop();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Server connected to $clean')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.fromLTRB(24, 16, 24, 24 + bottomInset),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.teal.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.dns_rounded, color: AppColors.teal, size: 24),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Server Connection', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 2),
                      const Text(
                        'Set the ScholarSetu Core API endpoint',
                        style: TextStyle(color: AppColors.muted, fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _urlCtrl,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: InputDecoration(
                labelText: 'Server Base URL',
                hintText: 'http://192.168.31.202:8000',
                prefixIcon: const Icon(Icons.link_rounded),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear_rounded),
                  onPressed: () => _urlCtrl.clear(),
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text('Quick presets:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.muted)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: _presets.map((preset) {
                return ActionChip(
                  label: Text('${preset.$1} (${preset.$2.replaceFirst("http://", "")})'),
                  onPressed: () {
                    setState(() {
                      _urlCtrl.text = preset.$2;
                      _testSuccess = null;
                      _testError = null;
                    });
                  },
                );
              }).toList(),
            ),
            if (_testSuccess != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green.shade300),
                ),
                child: Row(
                  children: [
                    Icon(Icons.check_circle_rounded, color: Colors.green.shade700, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _testSuccess!,
                        style: TextStyle(color: Colors.green.shade900, fontSize: 13, fontWeight: FontWeight.w500),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (_testError != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.error_outline_rounded, color: Colors.red.shade700, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _testError!,
                        style: TextStyle(color: Colors.red.shade900, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _testing ? null : _testConnection,
                    child: _testing
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Test Connection'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: _testing ? null : _save,
                    child: const Text('Save & Apply'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
