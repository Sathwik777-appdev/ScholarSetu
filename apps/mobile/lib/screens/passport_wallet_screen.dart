import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class PassportWalletScreen extends StatefulWidget {
  const PassportWalletScreen({Key? key}) : super(key: key);

  @override
  State<PassportWalletScreen> createState() => _PassportWalletScreenState();
}

class _PassportWalletScreenState extends State<PassportWalletScreen> {
  bool _isLoading = true;
  List<AttestationItem> _attestations = [];

  @override
  void initState() {
    super.initState();
    _loadPassport();
  }

  Future<void> _loadPassport() async {
    setState(() => _isLoading = true);
    final atts = await ApiService.getAttestations("stu-sunita-001");
    setState(() {
      _attestations = atts;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadPassport,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Concept Banner: Verify Once, Reuse Everywhere
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [AppTheme.primaryBlue, Colors.indigo.shade800],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.workspace_premium, color: Colors.amber, size: 24),
                              SizedBox(width: 8),
                              Text(
                                "Scholarship Passport",
                                style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                          SizedBox(height: 6),
                          Text(
                            "Verify once, reuse everywhere. Signed attestations eliminate repetitive document uploads across all 5 schemes and renewal years.",
                            style: TextStyle(color: Colors.white70, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),

                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("Digitally Signed Attestations", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        TextButton.icon(
                          icon: const Icon(Icons.download, size: 16),
                          label: const Text("Pull DigiLocker"),
                          onPressed: () {
                            ApiService.queueOfflineAction("DIGILOCKER_PULL", {"doc_type": "MARKSHEET_10"});
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text("DigiLocker document pulled into wallet successfully.")),
                            );
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),

                    ..._attestations.map((att) {
                      final bool isExpired = att.status == 'EXPIRED';
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    children: [
                                      Icon(
                                        isExpired ? Icons.cancel_outlined : Icons.verified,
                                        color: isExpired ? AppTheme.errorRed : AppTheme.successGreen,
                                        size: 20,
                                      ),
                                      const SizedBox(width: 8),
                                      Text(
                                        att.claimType.replaceAll('_', ' '),
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                      ),
                                    ],
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: isExpired ? Colors.red.shade50 : Colors.green.shade50,
                                      borderRadius: BorderRadius.circular(6),
                                      border: Border.all(color: isExpired ? Colors.red.shade300 : Colors.green.shade300),
                                    ),
                                    child: Text(
                                      isExpired ? "EXPIRED" : (att.isLifetime ? "LIFETIME VALID" : "ACTIVE"),
                                      style: TextStyle(
                                        color: isExpired ? AppTheme.errorRed : AppTheme.successGreen,
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Text("Source: ${att.source} • Method: ${att.method} • Confidence: ${(att.confidence * 100).toInt()}%",
                                  style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
                              const SizedBox(height: 6),
                              if (att.claimValue.isNotEmpty)
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(color: Colors.grey.shade50, borderRadius: BorderRadius.circular(6)),
                                  child: Text(
                                    att.claimValue.toString().replaceAll('{', '').replaceAll('}', ''),
                                    style: TextStyle(fontSize: 11.5, color: Colors.grey.shade800),
                                  ),
                                ),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  const Icon(Icons.key, size: 12, color: Colors.grey),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      "Ed25519 Sig: ${att.signature}",
                                      style: const TextStyle(fontFamily: 'monospace', fontSize: 10, color: Colors.grey),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  if (isExpired)
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: AppTheme.accentSaffron,
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                      ),
                                      onPressed: () {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          const SnackBar(content: Text("Initiating e-District Income Certificate renewal.")),
                                        );
                                      },
                                      child: const Text("Renew Now", style: TextStyle(fontSize: 11)),
                                    )
                                ],
                              )
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),
            ),
    );
  }
}
