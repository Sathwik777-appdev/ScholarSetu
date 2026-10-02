import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import '../state/providers.dart';
import 'theme.dart';
import 'widgets.dart';

class VerifierScreen extends ConsumerStatefulWidget {
  const VerifierScreen({super.key});
  @override
  ConsumerState<VerifierScreen> createState() => _VerifierScreenState();
}

class _VerifierScreenState extends ConsumerState<VerifierScreen> {
  final MobileScannerController _scannerController = MobileScannerController();
  bool _isScanning = true;

  @override
  void dispose() {
    _scannerController.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) async {
    if (!_isScanning) return;
    final List<Barcode> barcodes = capture.barcodes;
    for (final barcode in barcodes) {
      if (barcode.rawValue != null) {
        setState(() => _isScanning = false);
        await _verifyJws(barcode.rawValue!);
        break;
      }
    }
  }

  Future<void> _verifyJws(String jws) async {
    final api = ref.read(servicesProvider).api;
    try {
      final res = await api.post('/attestations/verify-jws', {'jws': jws});
      final isValid = res['is_valid'] == true;
      final reason = res['reason'];
      
      Map<String, dynamic>? payload;
      if (isValid) {
        try {
          final parts = jws.split('.');
          if (parts.length == 3) {
            String payloadBase64 = parts[1];
            while (payloadBase64.length % 4 != 0) {
              payloadBase64 += '=';
            }
            final payloadString = utf8.decode(base64Url.decode(payloadBase64));
            payload = jsonDecode(payloadString);
          }
        } catch (_) {}
      }

      if (!mounted) return;
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (c) => AlertDialog(
          title: Row(children: [
            Icon(isValid ? Icons.check_circle : Icons.error, color: isValid ? AppColors.teal : Colors.red),
            const SizedBox(width: 8),
            Text(isValid ? 'Authentic Document' : 'Verification Failed', style: const TextStyle(fontSize: 18)),
          ]),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (!isValid) Text(reason ?? 'Invalid signature', style: const TextStyle(color: Colors.red)),
              if (isValid && payload != null) ...[
                Text('Claim: ${payload['claim_type']}'),
                const SizedBox(height: 8),
                Text('Data: ${jsonEncode(payload['claim_value'])}', style: TextStyle(fontSize: 12, color: AppColors.muted)),
                const SizedBox(height: 8),
                Text('Source: ${payload['source']}'),
              ]
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(c);
                setState(() => _isScanning = true);
              },
              child: const Text('Scan Another'),
            )
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isScanning = true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline Verifier'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(sessionProvider.notifier).signOut(),
            tooltip: 'Sign Out',
          )
        ],
      ),
      body: Column(
        children: [
          Expanded(
            flex: 3,
            child: Container(
              margin: const EdgeInsets.fromLTRB(24, 24, 24, 12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: AppColors.ink900.withValues(alpha: 0.1), width: 8),
              ),
              clipBehavior: Clip.hardEdge,
              child: MobileScanner(
                controller: _scannerController,
                onDetect: _onDetect,
              ),
            ),
          ),
          Expanded(
            flex: 2,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    _isScanning ? Icons.qr_code_scanner_rounded : Icons.hourglass_top_rounded,
                    size: 48,
                    color: _isScanning ? AppColors.ink900 : AppColors.saffron,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _isScanning
                        ? 'Point camera at a ScholarSetu student QR code to instantly verify document authenticity.'
                        : 'Verifying signature...',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                      color: _isScanning ? AppColors.ink900 : AppColors.saffron,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
