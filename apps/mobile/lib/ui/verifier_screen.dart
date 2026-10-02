import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import '../state/providers.dart';
import '../theme.dart';
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
      final payload = res['payload'];

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
                Text('Data: ${jsonEncode(payload['claim_value'])}', style: const TextStyle(fontSize: 12, color: AppColors.muted)),
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
      appBar: AppBar(title: const Text('ScholarSetu Offline Verifier')),
      body: Stack(
        children: [
          MobileScanner(
            controller: _scannerController,
            onDetect: _onDetect,
          ),
          Positioned(
            bottom: 40,
            left: 20,
            right: 20,
            child: Card(
              color: Colors.white.withOpacity(0.9),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  _isScanning ? 'Point camera at student QR code' : 'Verifying...',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          )
        ],
      ),
    );
  }
}
