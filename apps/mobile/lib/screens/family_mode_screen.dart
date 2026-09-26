import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

class FamilyModeScreen extends StatefulWidget {
  const FamilyModeScreen({Key? key}) : super(key: key);

  @override
  State<FamilyModeScreen> createState() => _FamilyModeScreenState();
}

class _FamilyModeScreenState extends State<FamilyModeScreen> {
  bool _isLoading = true;
  Map<String, dynamic>? _familyData;

  @override
  void initState() {
    super.initState();
    _loadFamilyData();
  }

  Future<void> _loadFamilyData() async {
    setState(() => _isLoading = true);
    final data = await ApiService.getFamilyDashboard("hh_hansda_001");
    setState(() {
      _familyData = data;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text("Family Mode (Shared Phone)")),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final guardian = _familyData?['guardian_name'] ?? "Babulal Hansda (Father)";
    final List students = _familyData?['students'] ?? [];

    return Scaffold(
      appBar: AppBar(
        title: const Text("Family Mode (Shared Phone)"),
        backgroundColor: AppTheme.tribalTeal,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Guardian Banner
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.tribalTeal.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.tribalTeal.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: AppTheme.tribalTeal,
                    child: const Icon(Icons.family_restroom, color: Colors.white, size: 28),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(guardian, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        const SizedBox(height: 2),
                        const Text("Household ID: HH-JH-DUMKA-001", style: TextStyle(fontSize: 12, color: Colors.grey)),
                        const SizedBox(height: 2),
                        const Text("2 ST Beneficiary Students Linked", style: TextStyle(fontSize: 12, color: AppTheme.tribalTeal, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const Text("Children's Scholarships Across Portals", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),

            ...students.map((st) {
              final studentInfo = st['student'] ?? {};
              final List apps = st['applications'] ?? [];
              final double rec = (st['total_received'] as num?)?.toDouble() ?? 0.0;
              final bool isCredited = rec > 0;

              return Card(
                elevation: 2,
                margin: const EdgeInsets.only(bottom: 12),
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
                              CircleAvatar(
                                radius: 18,
                                backgroundColor: isCredited ? AppTheme.successGreen.withOpacity(0.15) : AppTheme.primaryBlue.withOpacity(0.15),
                                child: Text(
                                  studentInfo['name']?.substring(0, 1) ?? "S",
                                  style: TextStyle(
                                    color: isCredited ? AppTheme.successGreen : AppTheme.primaryBlue,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(studentInfo['name'] ?? "", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                                  Text(studentInfo['aadhaar_ref'] ?? "", style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                                ],
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: isCredited ? Colors.green.shade50 : Colors.blue.shade50,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: isCredited ? Colors.green.shade300 : Colors.blue.shade300),
                            ),
                            child: Text(
                              isCredited ? "CREDITED" : "IN REVIEW",
                              style: TextStyle(
                                color: isCredited ? AppTheme.successGreen : AppTheme.primaryBlue,
                                fontWeight: FontWeight.bold,
                                fontSize: 11,
                              ),
                            ),
                          )
                        ],
                      ),
                      const Divider(height: 20),
                      if (apps.isNotEmpty) ...[
                        Text("Scheme: ${apps[0]['scheme']} (${apps[0]['academic_year']})", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 4),
                        Text("Next Action: ${apps[0]['next_action'] ?? 'None'}", style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
                      ],
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Disbursed: ₹${rec.toStringAsFixed(0)}", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.successGreen)),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.tribalTeal,
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            ),
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text("Switched active profile to ${studentInfo['name']}")),
                              );
                              Navigator.pop(context);
                            },
                            child: const Text("Switch to Profile", style: TextStyle(fontSize: 12)),
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
    );
  }
}
