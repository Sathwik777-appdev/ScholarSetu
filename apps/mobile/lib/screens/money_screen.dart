import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class MoneyScreen extends StatefulWidget {
  const MoneyScreen({Key? key}) : super(key: key);

  @override
  State<MoneyScreen> createState() => _MoneyScreenState();
}

class _MoneyScreenState extends State<MoneyScreen> {
  bool _isLoading = true;
  MoneyViewData? _moneyData;

  @override
  void initState() {
    super.initState();
    _loadMoneyView();
  }

  Future<void> _loadMoneyView() async {
    setState(() => _isLoading = true);
    final data = await ApiService.getMoneyView("stu-sunita-001");
    setState(() {
      _moneyData = data;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadMoneyView,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // DBT Summary Card
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [AppTheme.tribalTeal, Colors.teal.shade800],
                        ),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Disbursement Overview (DBT)", style: TextStyle(color: Colors.white70, fontSize: 13)),
                          const SizedBox(height: 6),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text("Total Sanctioned", style: TextStyle(color: Colors.white70, fontSize: 11)),
                                  Text("₹${_moneyData?.sanctioned.toStringAsFixed(0) ?? '0'}",
                                      style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text("Total Credited", style: TextStyle(color: Colors.white70, fontSize: 11)),
                                  Text("₹${_moneyData?.credited.toStringAsFixed(0) ?? '0'}",
                                      style: const TextStyle(color: Colors.greenAccent, fontSize: 22, fontWeight: FontWeight.bold)),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text("Pending", style: TextStyle(color: Colors.white70, fontSize: 11)),
                                  Text("₹${_moneyData?.pending.toStringAsFixed(0) ?? '0'}",
                                      style: const TextStyle(color: Colors.amberAccent, fontSize: 22, fontWeight: FontWeight.bold)),
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),

                    // DBT Guardian Health Pre-Sanction Check (Scene 4)
                    Card(
                      color: Colors.red.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.shield_outlined, color: AppTheme.errorRed, size: 22),
                                const SizedBox(width: 8),
                                const Text(
                                  "DBT Guardian Health Status: ACTION REQUIRED",
                                  style: TextStyle(color: AppTheme.errorRed, fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                              ],
                            ),
                            const Divider(height: 18),
                            _buildCheckRow("Aadhaar Seeded for DBT/NPCI", false, "Not Linked (Disbursement Blocked)"),
                            _buildCheckRow("Bank Account Active", true, "Active (State Bank of India)"),
                            _buildCheckRow("Name Match on Account vs Aadhaar", true, "95% Confidence Match"),
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text("Hindi Fix Instructions / सुधार निर्देश:",
                                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.errorRed)),
                                  const SizedBox(height: 4),
                                  const Text(
                                    "आपका आधार सरकारी भुगतान के लिए बैंक खाते से जुड़ा नहीं है। अपना आधार कार्ड लेकर अपनी बैंक शाखा जाएं और DBT/NPCI आधार सीडिंग करवाएं।",
                                    style: TextStyle(fontSize: 12.5),
                                  ),
                                  const SizedBox(height: 6),
                                  const Text(
                                    "Fix Steps: 1. Carry Aadhaar Card to branch 2. Ask specifically for NPCI Aadhaar seeding (not just KYC link) 3. Return here to re-check.",
                                    style: TextStyle(fontSize: 11.5, color: Colors.black87),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 10),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.refresh, size: 16),
                                label: const Text("Re-run DBT Guardian Health Check"),
                                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryBlue),
                                onPressed: () {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text("Pre-sanction DBT check re-evaluated against PFMS/NPCI mapper mock.")),
                                  );
                                },
                              ),
                            )
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 18),

                    const Text("Scheduled Instalments", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),

                    ...?_moneyData?.instalments.map((inst) {
                      return Card(
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: Colors.blue.shade50,
                            child: Text("${inst['instalment_no']}", style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primaryBlue)),
                          ),
                          title: Text(inst['type'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                          subtitle: Text("Target Date: ${inst['date']} • Status: ${inst['status']}", style: const TextStyle(fontSize: 12)),
                          trailing: Text(
                            "₹${(inst['amount'] as num).toStringAsFixed(0)}",
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.primaryBlue),
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

  Widget _buildCheckRow(String title, bool pass, String detail) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(pass ? Icons.check_circle : Icons.cancel, color: pass ? AppTheme.successGreen : AppTheme.errorRed, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
          ),
          Text(detail, style: TextStyle(fontSize: 11, color: pass ? AppTheme.successGreen : AppTheme.errorRed, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
