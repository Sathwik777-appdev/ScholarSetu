import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class PathwayScreen extends StatefulWidget {
  const PathwayScreen({Key? key}) : super(key: key);

  @override
  State<PathwayScreen> createState() => _PathwayScreenState();
}

class _PathwayScreenState extends State<PathwayScreen> {
  bool _isLoading = true;
  PathwayData? _pathway;

  @override
  void initState() {
    super.initState();
    _loadPathway();
  }

  Future<void> _loadPathway() async {
    setState(() => _isLoading = true);
    final p = await ApiService.getPathway("stu-sunita-001");
    setState(() {
      _pathway = p;
      _isLoading = false;
    });
  }

  final List<Map<String, dynamic>> _ladderRungs = [
    {
      'title': 'Pre-Matric Scholarship',
      'target': 'Classes 9–10',
      'scheme': 'PRE_MATRIC',
      'portal': 'State / NSP',
      'status': 'COMPLETED',
      'icon': Icons.school,
    },
    {
      'title': 'Post-Matric Scholarship',
      'target': 'Class 11 to Post-Graduate',
      'scheme': 'POST_MATRIC',
      'portal': 'NSP',
      'status': 'CURRENT_TARGET',
      'icon': Icons.account_balance,
    },
    {
      'title': 'Top Class Education',
      'target': 'Premier Institutions (IIT/NIT/AIIMS)',
      'scheme': 'TOP_CLASS',
      'portal': 'NSP',
      'status': 'UPCOMING',
      'icon': Icons.star,
    },
    {
      'title': 'National Fellowship (NFST)',
      'target': 'M.Phil / PhD Scholars (NET/JRF)',
      'scheme': 'NFST',
      'portal': 'SFMP (Canara Bank)',
      'status': 'UPCOMING',
      'icon': Icons.psychology,
    },
    {
      'title': 'National Overseas Scholarship (NOS)',
      'target': 'Master\'s & PhD Studies Abroad',
      'scheme': 'NOS',
      'portal': 'NOS Portal',
      'status': 'UPCOMING',
      'icon': Icons.flight_takeoff,
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadPathway,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Transition Nudge Card (Scene 2)
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade50,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.amber.shade400),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.bolt, color: Colors.amber.shade900, size: 24),
                              const SizedBox(width: 8),
                              Text(
                                "Transition Nudge Triggered",
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.amber.shade900),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _pathway?.transitionTrigger ?? "Class 10 Matriculation result verified in DigiLocker.",
                            style: TextStyle(fontSize: 13, color: Colors.brown.shade900),
                          ),
                          const SizedBox(height: 10),
                          ElevatedButton.icon(
                            icon: const Icon(Icons.arrow_forward),
                            label: const Text("Apply for Post-Matric (Pre-Filled)"),
                            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentSaffron),
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text("Pre-filled Post-Matric form generated! ST Attestation auto-attached.")),
                              );
                            },
                          )
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    const Text("Lifetime Scholarship Pathway Ladder", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    const Text("Schemes treated as a connected ladder, preventing dropout at transitions.",
                        style: TextStyle(fontSize: 12, color: Colors.grey)),
                    const SizedBox(height: 16),

                    // Ladder Rungs
                    ...List.generate(_ladderRungs.length, (index) {
                      final rung = _ladderRungs[index];
                      final bool isCurrent = rung['status'] == 'CURRENT_TARGET';
                      final bool isCompleted = rung['status'] == 'COMPLETED';

                      Color cardColor = Colors.white;
                      Color borderColor = Colors.grey.shade300;
                      if (isCurrent) {
                        cardColor = Colors.blue.shade50;
                        borderColor = AppTheme.primaryBlue;
                      } else if (isCompleted) {
                        cardColor = Colors.green.shade50;
                        borderColor = AppTheme.successGreen;
                      }

                      return Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: cardColor,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: borderColor, width: isCurrent ? 1.5 : 1),
                        ),
                        child: Row(
                          children: [
                            CircleAvatar(
                              backgroundColor: isCompleted
                                  ? AppTheme.successGreen
                                  : (isCurrent ? AppTheme.primaryBlue : Colors.grey.shade300),
                              child: Icon(rung['icon'], color: Colors.white, size: 20),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(rung['title'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                                  Text("${rung['target']} • ${rung['portal']}", style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
                                ],
                              ),
                            ),
                            if (isCompleted)
                              const Icon(Icons.check_circle, color: AppTheme.successGreen, size: 22)
                            else if (isCurrent)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(color: AppTheme.primaryBlue, borderRadius: BorderRadius.circular(6)),
                                child: const Text("YOU ARE HERE", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                              )
                            else
                              const Icon(Icons.lock_outline, color: Colors.grey, size: 20),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
            ),
    );
  }
}
