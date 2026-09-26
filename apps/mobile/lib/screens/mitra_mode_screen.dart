import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class MitraModeScreen extends StatefulWidget {
  const MitraModeScreen({Key? key}) : super(key: key);

  @override
  State<MitraModeScreen> createState() => _MitraModeScreenState();
}

class _MitraModeScreenState extends State<MitraModeScreen> {
  bool _isSessionActive = false;
  final TextEditingController _helperPhoneCtrl = TextEditingController(text: "9876123450");
  final TextEditingController _otpCtrl = TextEditingController(text: "123456");
  String _selectedScope = "UPLOAD_DOCS";
  int _remainingMinutes = 30;

  void _startSession() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Student OTP Consent"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("A 6-digit consent OTP has been sent to Sunita's registered mobile number."),
            const SizedBox(height: 12),
            TextField(
              controller: _otpCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: "Enter 6-digit Student OTP",
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancel")),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              setState(() {
                _isSessionActive = true;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Mitra Assisted Session Started (30 mins). All actions audit-logged.")),
              );
            },
            child: const Text("Verify & Start"),
          )
        ],
      ),
    );
  }

  void _endSession() {
    setState(() {
      _isSessionActive = false;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Mitra Session ended and signed into audit log.")),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Mitra (Assisted) Mode"),
        backgroundColor: AppTheme.tribalTeal,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.teal.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.teal.shade200),
              ),
              child: Row(
                children: [
                  const Icon(Icons.security, color: AppTheme.tribalTeal, size: 24),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "Consent-based assisted access for Ashram school teachers, hostel wardens & CSC operators.",
                      style: TextStyle(fontSize: 12.5, color: Colors.teal.shade900),
                    ),
                  )
                ],
              ),
            ),
            const SizedBox(height: 20),

            if (!_isSessionActive) ...[
              const Text("Initiate Assisted Session", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              TextField(
                controller: _helperPhoneCtrl,
                decoration: const InputDecoration(
                  labelText: "Registered Helper Phone Number",
                  prefixIcon: Icon(Icons.phone),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                value: _selectedScope,
                decoration: const InputDecoration(
                  labelText: "Delegated Permission Scope",
                  prefixIcon: Icon(Icons.admin_panel_settings_outlined),
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: "UPLOAD_DOCS", child: Text("Upload Documents Only")),
                  DropdownMenuItem(value: "FILL_FORM", child: Text("Fill Application Form")),
                  DropdownMenuItem(value: "VIEW_STATUS", child: Text("View Status & Deficiencies")),
                  DropdownMenuItem(value: "FULL_ACCESS", child: Text("Full Assisted Access")),
                ],
                onChanged: (val) {
                  setState(() => _selectedScope = val!);
                },
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.verified_user),
                  label: const Text("Request Student OTP & Start Session"),
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.tribalTeal),
                  onPressed: _startSession,
                ),
              )
            ] else ...[
              Card(
                color: Colors.green.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.check_circle, color: AppTheme.successGreen),
                              SizedBox(width: 8),
                              Text("Active Session", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.successGreen)),
                            ],
                          ),
                          Chip(label: Text("$_remainingMinutes mins remaining", style: const TextStyle(fontSize: 11))),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text("Helper: Ashram School Headmaster (${_helperPhoneCtrl.text})", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                      Text("Student: Sunita Hansda (OTP Verified)", style: TextStyle(fontSize: 13, color: Colors.grey.shade700)),
                      Text("Scope: $_selectedScope", style: const TextStyle(fontSize: 13, color: AppTheme.tribalTeal, fontWeight: FontWeight.bold)),
                      const Divider(height: 24),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              icon: const Icon(Icons.upload_file, size: 16),
                              label: const Text("Assisted Upload", style: TextStyle(fontSize: 12)),
                              onPressed: () {
                                ApiService.queueOfflineAction("ASSISTED_DOCUMENT_UPLOAD", {"by": _helperPhoneCtrl.text});
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text("Document uploaded on behalf of student (Audit event recorded).")),
                                );
                              },
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: ElevatedButton(
                              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.errorRed),
                              onPressed: _endSession,
                              child: const Text("End Session", style: TextStyle(fontSize: 12)),
                            ),
                          )
                        ],
                      )
                    ],
                  ),
                ),
              )
            ],

            const SizedBox(height: 24),
            const Text("Recent Audit Trail", style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            ListTile(
              dense: true,
              leading: const Icon(Icons.history, color: Colors.grey),
              title: const Text("Mitra Session #MS-0891"),
              subtitle: const Text("Hostel Warden uploaded Class 10 marksheet • 2026-09-20"),
              trailing: const Icon(Icons.check, color: AppTheme.successGreen, size: 18),
            ),
          ],
        ),
      ),
    );
  }
}
