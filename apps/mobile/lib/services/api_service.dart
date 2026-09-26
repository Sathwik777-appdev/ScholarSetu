import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';

class ApiService {
  // Configurable base URL: Android emulator uses 10.0.2.2, iOS/Web/Mac uses localhost
  static String baseUrl = 'http://localhost:8000/v1';

  // Toggle to simulate offline mode
  static bool isSimulatedOffline = false;

  // Local outbox for offline queued actions
  static final List<Map<String, dynamic>> offlineOutbox = [];

  static Future<Map<String, dynamic>> getStudentDashboard(String studentId) async {
    if (isSimulatedOffline) {
      return _getMockDashboard(studentId);
    }
    try {
      final res = await http.get(Uri.parse('$baseUrl/me/dashboard?student_id=$studentId')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return _getMockDashboard(studentId);
  }

  static Future<Map<String, dynamic>> getFamilyDashboard(String householdId) async {
    if (isSimulatedOffline) {
      return _getMockFamilyDashboard();
    }
    try {
      final res = await http.get(Uri.parse('$baseUrl/me/household?household_id=$householdId')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return _getMockFamilyDashboard();
  }

  static Future<List<TimelineEventItem>> getTimeline(String appId) async {
    if (isSimulatedOffline) {
      return _getMockTimeline(appId);
    }
    try {
      final res = await http.get(Uri.parse('$baseUrl/applications/$appId/timeline')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        final List list = json.decode(res.body);
        return list.map((e) => TimelineEventItem.fromJson(e)).toList();
      }
    } catch (_) {}
    return _getMockTimeline(appId);
  }

  static Future<List<AttestationItem>> getAttestations(String studentId) async {
    if (isSimulatedOffline) {
      return _getMockAttestations();
    }
    try {
      final res = await http.get(Uri.parse('$baseUrl/me/attestations?student_id=$studentId')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final Map<String, dynamic> attMap = data['attestations'] ?? {};
        final List<AttestationItem> items = [];
        attMap.forEach((key, list) {
          if (list is List) {
            for (var a in list) {
              items.add(AttestationItem.fromJson(a));
            }
          }
        });
        return items;
      }
    } catch (_) {}
    return _getMockAttestations();
  }

  static Future<PathwayData> getPathway(String studentId) async {
    if (isSimulatedOffline) {
      return PathwayData(
        currentScheme: 'PRE_MATRIC',
        currentState: 'CREDITED',
        ladderPosition: 0,
        nextEligible: 'POST_MATRIC',
        transitionTrigger: 'Class 10 Matriculation marksheet detected in DigiLocker',
        preFilledAvailable: true,
      );
    }
    try {
      final res = await http.get(Uri.parse('$baseUrl/me/pathway?student_id=$studentId')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return PathwayData.fromJson(json.decode(res.body));
      }
    } catch (_) {}
    return PathwayData(
      currentScheme: 'PRE_MATRIC',
      currentState: 'CREDITED',
      ladderPosition: 0,
      nextEligible: 'POST_MATRIC',
      transitionTrigger: 'Class 10 Matriculation marksheet detected in DigiLocker',
      preFilledAvailable: true,
    );
  }

  static Future<MoneyViewData> getMoneyView(String studentId) async {
    if (isSimulatedOffline) {
      return _getMockMoneyView();
    }
    try {
      final res = await http.get(Uri.parse('$baseUrl/me/payments?student_id=$studentId')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return MoneyViewData.fromJson(json.decode(res.body));
      }
    } catch (_) {}
    return _getMockMoneyView();
  }

  static Future<String> chatWithJAGO(String message, String language) async {
    if (isSimulatedOffline) {
      if (message.toLowerCase().contains('paisa') || message.toLowerCase().contains('kab')) {
        return "आपकी Post-Matric छात्रवृत्ति स्वीकृत हो चुकी है। भुगतान ₹7,500 की प्रक्रिया जारी है। लेकिन DBT Guardian जांच के अनुसार आपके बैंक खाते में आधार सीडिंग अधूरी है। कृपया शाखा पर जाएं।";
      }
      return "नमस्ते! मैं जागो हूं। आप छात्रवृत्ति की स्थिति, आवश्यक दस्तावेज और भुगतान की जानकारी पूछ सकते हैं।";
    }
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/jago/chat'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'message': message, 'language': language, 'channel': 'app'}),
      ).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        return data['response_text'] ?? '';
      }
    } catch (_) {}
    return "आपकी Post-Matric छात्रवृत्ति स्वीकृत हो चुकी है। भुगतान प्रक्रियाधीन है।";
  }

  static void queueOfflineAction(String actionType, Map<String, dynamic> payload) {
    offlineOutbox.add({
      'action': actionType,
      'payload': payload,
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  static Future<int> syncOfflineOutbox() async {
    final count = offlineOutbox.length;
    offlineOutbox.clear();
    return count;
  }

  // --- Mock Offline Data ---
  static Map<String, dynamic> _getMockDashboard(String studentId) {
    if (studentId == 'stu-rahul-002') {
      return {
        'student': {'id': 'stu-rahul-002', 'name': 'Rahul Hansda', 'aadhaar_ref': 'XXXX-XXXX-9914'},
        'applications': [
          {
            'id': 'APP-PRM-2025-004192',
            'scheme': 'PRE_MATRIC',
            'academic_year': '2025-26',
            'current_state': 'CREDITED',
            'next_action': 'Renewal due for Class 10 next academic session',
            'money_received': 7000.0,
          }
        ],
        'total_received': 7000.0,
      };
    }
    return {
      'student': {'id': 'stu-sunita-001', 'name': 'Sunita Hansda', 'aadhaar_ref': 'XXXX-XXXX-4912'},
      'applications': [
        {
          'id': 'APP-PM-2026-000812',
          'scheme': 'POST_MATRIC',
          'academic_year': '2026-27',
          'current_state': 'AUTHORITY_VERIFICATION',
          'next_action': 'Aadhaar-bank seeding required at branch (DBT Guardian alert)',
          'money_received': 0.0,
        }
      ],
      'total_received': 0.0,
    };
  }

  static Map<String, dynamic> _getMockFamilyDashboard() {
    return {
      'household_id': 'hh_hansda_001',
      'guardian_name': 'Babulal Hansda (Father)',
      'students': [
        _getMockDashboard('stu-sunita-001'),
        _getMockDashboard('stu-rahul-002'),
      ]
    };
  }

  static List<TimelineEventItem> _getMockTimeline(String appId) {
    return [
      TimelineEventItem(
        id: 'evt_03',
        eventType: 'ProvisionalIdentityMatch',
        occurredAt: DateTime.now().subtract(const Duration(days: 2)).toIso8601String(),
        source: 'SCHOLARSETU',
        eventHash: 'sha256:7f8e9d0a',
        payload: {'note': 'Hansda vs Hansdah transliteration difference. Routed to review queue without blocking.'},
      ),
      TimelineEventItem(
        id: 'evt_02',
        eventType: 'InstituteVerified',
        occurredAt: DateTime.now().subtract(const Duration(days: 4)).toIso8601String(),
        source: 'NSP',
        eventHash: 'sha256:4a8b9c0d',
        payload: {'verified_by': 'Principal, Dumka Govt College', 'aishe_code': 'C-41290'},
      ),
      TimelineEventItem(
        id: 'evt_01',
        eventType: 'ApplicationSubmitted',
        occurredAt: DateTime.now().subtract(const Duration(days: 5)).toIso8601String(),
        source: 'SCHOLARSETU',
        eventHash: 'sha256:1a2b3c4d',
        payload: {'reused_attestations': ['ST_STATUS', 'IDENTITY']},
      ),
    ];
  }

  static List<AttestationItem> _getMockAttestations() {
    return [
      AttestationItem(
        attestationId: 'att_st_stu-sunita-001',
        claimType: 'ST_STATUS',
        source: 'DIGILOCKER',
        method: 'API',
        confidence: 0.99,
        issueDate: '2025-11-20',
        status: 'ACTIVE',
        signature: 'ed25519:6a7b8c9d0e1f',
        claimValue: {'tribe': 'Santal', 'pvtg': false, 'state': 'Jharkhand'},
      ),
      AttestationItem(
        attestationId: 'att_id_stu-sunita-001',
        claimType: 'IDENTITY',
        source: 'UIDAI',
        method: 'API',
        confidence: 1.0,
        issueDate: '2025-11-20',
        status: 'ACTIVE',
        signature: 'ed25519:3b4c5d6e7f8a',
        claimValue: {'name': 'Sunita Hansda', 'dob': '2008-04-12'},
      ),
      AttestationItem(
        attestationId: 'att_inc_stu-sunita-001',
        claimType: 'INCOME',
        source: 'EDISTRICT',
        method: 'API',
        confidence: 0.95,
        issueDate: '2025-08-15',
        expiryDate: '2026-08-15',
        status: 'EXPIRED',
        signature: 'ed25519:9e8f7a6b5c4d',
        claimValue: {'annual_income': 120000, 'fy': '2024-25'},
      ),
    ];
  }

  static MoneyViewData _getMockMoneyView() {
    return MoneyViewData(
      applicationId: 'APP-PM-2026-000812',
      sanctioned: 14500.0,
      credited: 0.0,
      failed: 0.0,
      pending: 14500.0,
      instalments: [
        {'instalment_no': 1, 'type': 'Maintenance Allowance', 'amount': 7500.0, 'status': 'PAYMENT_INITIATED', 'date': '2026-09-22'},
        {'instalment_no': 2, 'type': 'Tuition & Compulsory Fees', 'amount': 7000.0, 'status': 'SANCTIONED', 'date': '2026-10-15'},
      ],
    );
  }
}
