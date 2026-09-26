import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import '../models/models.dart';
import 'family_mode_screen.dart';
import 'mitra_mode_screen.dart';
import 'timeline_screen.dart';
import 'passport_wallet_screen.dart';
import 'pathway_screen.dart';
import 'money_screen.dart';
import 'jago_chat_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _selectedIndex = 0;
  bool _isLoading = true;
  Map<String, dynamic>? _dashboardData;
  String _activeStudentId = "stu-sunita-001";

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final data = await ApiService.getStudentDashboard(_activeStudentId);
    setState(() {
      _dashboardData = data;
      _isLoading = false;
    });
  }

  Widget _buildHomeTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    final student = _dashboardData?['student'] ?? {};
    final List apps = _dashboardData?['applications'] ?? [];
    final double totalRec = (_dashboardData?['total_received'] as num?)?.toDouble() ?? 0.0;

    return RefreshIndicator(
      onRefresh: _loadData,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Mode Banners (Offline, Mitra, Family)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.people_outline, size: 18),
                      label: const Text("Family Mode", style: TextStyle(fontSize: 13)),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.primaryBlue,
                        side: const BorderSide(color: AppTheme.primaryBlue),
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                      onPressed: () {
                        Navigator.push(context, MaterialPageRoute(builder: (_) => const FamilyModeScreen()));
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.handshake_outlined, size: 18),
                      label: const Text("Mitra Mode", style: TextStyle(fontSize: 13)),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.tribalTeal,
                        side: const BorderSide(color: AppTheme.tribalTeal),
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                      onPressed: () {
                        Navigator.push(context, MaterialPageRoute(builder: (_) => const MitraModeScreen()));
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    tooltip: "Toggle Offline Simulation",
                    icon: Icon(
                      ApiService.isSimulatedOffline ? Icons.cloud_off : Icons.cloud_done,
                      color: ApiService.isSimulatedOffline ? AppTheme.errorRed : AppTheme.successGreen,
                    ),
                    onPressed: () {
                      setState(() {
                        ApiService.isSimulatedOffline = !ApiService.isSimulatedOffline;
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(ApiService.isSimulatedOffline
                              ? "Offline Mode Enabled. Using local SQLCipher encrypted store."
                              : "Online Mode Active. Connected to Core API."),
                          duration: const Duration(seconds: 2),
                        ),
                      );
                      _loadData();
                    },
                  )
                ],
              ),
            ),

            if (ApiService.isSimulatedOffline)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.amber.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.amber.shade800),
                ),
                child: Row(
                  children: [
                    Icon(Icons.wifi_off, size: 18, color: Colors.amber.shade900),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        "Offline Mode: Actions queued in outbox for sync.",
                        style: TextStyle(color: Colors.amber.shade900, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),

            // Profile Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 28,
                      backgroundColor: AppTheme.primaryBlue.withOpacity(0.12),
                      child: const Text("SH", style: TextStyle(color: AppTheme.primaryBlue, fontWeight: FontWeight.bold, fontSize: 20)),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(student['name'] ?? "Sunita Hansda", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 2),
                          Text("Aadhaar: ${student['aadhaar_ref'] ?? 'XXXX-XXXX-4912'} • Santal Tribe", style: TextStyle(color: Colors.grey.shade700, fontSize: 13)),
                          const SizedBox(height: 2),
                          const Text("Dumka, Jharkhand • Class 11", style: TextStyle(color: AppTheme.tribalTeal, fontWeight: FontWeight.w600, fontSize: 13)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Pathway Quick Nudge (Scene 2)
            GestureDetector(
              onTap: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const PathwayScreen()));
              },
              child: Card(
                color: Colors.blue.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(color: AppTheme.primaryBlue, borderRadius: BorderRadius.circular(8)),
                        child: const Icon(Icons.trending_up, color: Colors.white, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text("Ladder Pathway Nudge", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.primaryBlue)),
                            const SizedBox(height: 2),
                            Text("Class 10 Passed! Pre-filled Post-Matric application ready. ST Attestation reused.", style: TextStyle(fontSize: 12, color: Colors.blue.shade900)),
                          ],
                        ),
                      ),
                      const Icon(Icons.arrow_forward_ios, size: 14, color: AppTheme.primaryBlue),
                    ],
                  ),
                ),
              ),
            ),

            // Pending Action: DBT Guardian Warning (Scene 4)
            Card(
              color: Colors.deepOrange.shade50,
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.warning_amber_rounded, color: Colors.deepOrange.shade800, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          "DBT Guardian Alert (Action Required)",
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.deepOrange.shade900),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      "Aadhaar is not linked to bank account for DBT payments. Visit branch with Aadhaar to avoid disbursement failure.",
                      style: TextStyle(fontSize: 12.5, color: Colors.deepOrange.shade900),
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton.icon(
                        icon: const Icon(Icons.arrow_forward, size: 16),
                        label: const Text("View Remediation Steps"),
                        style: TextButton.styleFrom(foregroundColor: Colors.deepOrange.shade900),
                        onPressed: () {
                          Navigator.push(context, MaterialPageRoute(builder: (_) => const MoneyScreen()));
                        },
                      ),
                    )
                  ],
                ),
              ),
            ),

            const Padding(
              padding: EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Text("Active Applications", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),

            // Application Cards
            if (apps.isEmpty)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text("No active applications"),
              )
            else
              ...apps.map((app) {
                final String state = app['current_state'] ?? 'SUBMITTED';
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(app['scheme'] ?? "POST_MATRIC", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.indigo.shade50,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: Colors.indigo.shade200),
                              ),
                              child: Text(
                                state.replaceAll('_', ' '),
                                style: TextStyle(color: Colors.indigo.shade900, fontWeight: FontWeight.bold, fontSize: 11),
                              ),
                            )
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text("Application ID: ${app['id']}", style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
                        const SizedBox(height: 4),
                        Text("Academic Session: ${app['academic_year'] ?? '2026-27'}", style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
                        const Divider(height: 18),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text("Amount Disbursed", style: TextStyle(fontSize: 11, color: Colors.grey)),
                                Text("₹${(app['money_received'] ?? 0).toStringAsFixed(0)}", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.successGreen)),
                              ],
                            ),
                            ElevatedButton.icon(
                              icon: const Icon(Icons.history, size: 16),
                              label: const Text("View Timeline", style: TextStyle(fontSize: 12)),
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              ),
                              onPressed: () {
                                Navigator.push(context, MaterialPageRoute(builder: (_) => TimelineScreen(applicationId: app['id'])));
                              },
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

  @override
  Widget build(BuildContext context) {
    final List<Widget> pages = [
      _buildHomeTab(),
      const PassportWalletScreen(),
      const PathwayScreen(),
      const MoneyScreen(),
      const JAGOChatScreen(),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.school, color: Colors.white, size: 24),
            const SizedBox(width: 8),
            const Text("ScholarSetu"),
            const Spacer(),
            IconButton(
              icon: const Icon(Icons.headset_mic_outlined),
              tooltip: "JAGO Voice Assistant",
              onPressed: () {
                setState(() => _selectedIndex = 4);
              },
            ),
          ],
        ),
      ),
      body: pages[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (idx) {
          setState(() => _selectedIndex = idx);
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: "Dashboard"),
          NavigationDestination(icon: Icon(Icons.verified_outlined), selectedIcon: Icon(Icons.verified), label: "Passport"),
          NavigationDestination(icon: Icon(Icons.ladder_outlined), selectedIcon: Icon(Icons.ladder), label: "Pathway"),
          NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), selectedIcon: Icon(Icons.account_balance_wallet), label: "Money"),
          NavigationDestination(icon: Icon(Icons.smart_toy_outlined), selectedIcon: Icon(Icons.smart_toy), label: "JAGO AI"),
        ],
      ),
    );
  }
}
