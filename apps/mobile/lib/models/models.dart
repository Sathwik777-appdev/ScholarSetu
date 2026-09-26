class Student {
  final String id;
  final String name;
  final String aadhaarMasked;
  final String state;
  final String district;
  final String tribe;
  final String preferredLanguage;

  Student({
    required this.id,
    required this.name,
    required this.aadhaarMasked,
    required this.state,
    required this.district,
    required this.tribe,
    this.preferredLanguage = 'hi',
  });

  factory Student.fromJson(Map<String, dynamic> json) {
    return Student(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      aadhaarMasked: json['aadhaar_ref'] ?? 'XXXX-XXXX-4912',
      state: json['state'] ?? 'Jharkhand',
      district: json['district'] ?? 'Dumka',
      tribe: json['tribe'] ?? 'Santal',
      preferredLanguage: json['preferred_language'] ?? 'hi',
    );
  }
}

class ApplicationItem {
  final String id;
  final String scheme;
  final String academicYear;
  final String currentState;
  final String? nextAction;
  final double moneyReceived;
  final String sourceSystem;

  ApplicationItem({
    required this.id,
    required this.scheme,
    required this.academicYear,
    required this.currentState,
    this.nextAction,
    this.moneyReceived = 0.0,
    this.sourceSystem = 'NSP',
  });

  factory ApplicationItem.fromJson(Map<String, dynamic> json) {
    return ApplicationItem(
      id: json['id'] ?? '',
      scheme: json['scheme'] ?? 'POST_MATRIC',
      academicYear: json['academic_year'] ?? '2026-27',
      currentState: json['current_state'] ?? json['canonical_state'] ?? 'SUBMITTED',
      nextAction: json['next_action'],
      moneyReceived: (json['money_received'] as num?)?.toDouble() ?? 0.0,
      sourceSystem: json['source_system'] ?? 'NSP',
    );
  }
}

class TimelineEventItem {
  final String id;
  final String eventType;
  final String occurredAt;
  final String source;
  final String eventHash;
  final Map<String, dynamic> payload;

  TimelineEventItem({
    required this.id,
    required this.eventType,
    required this.occurredAt,
    required this.source,
    required this.eventHash,
    required this.payload,
  });

  factory TimelineEventItem.fromJson(Map<String, dynamic> json) {
    return TimelineEventItem(
      id: json['id'] ?? '',
      eventType: json['event_type'] ?? '',
      occurredAt: json['occurred_at'] ?? '',
      source: json['source'] ?? 'SCHOLARSETU',
      eventHash: json['event_hash'] ?? '',
      payload: json['payload'] ?? {},
    );
  }
}

class AttestationItem {
  final String attestationId;
  final String claimType;
  final String source;
  final String method;
  final double confidence;
  final String issueDate;
  final String? expiryDate;
  final String status;
  final String signature;
  final Map<String, dynamic> claimValue;

  AttestationItem({
    required this.attestationId,
    required this.claimType,
    required this.source,
    required this.method,
    required this.confidence,
    required this.issueDate,
    this.expiryDate,
    required this.status,
    required this.signature,
    required this.claimValue,
  });

  bool get isLifetime => expiryDate == null;
  bool get isActive => status == 'ACTIVE';

  factory AttestationItem.fromJson(Map<String, dynamic> json) {
    return AttestationItem(
      attestationId: json['attestation_id'] ?? '',
      claimType: json['claim_type'] ?? '',
      source: json['source'] ?? '',
      method: json['method'] ?? 'API',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 1.0,
      issueDate: json['issue_date'] ?? '',
      expiryDate: json['expiry_date'],
      status: json['status'] ?? 'ACTIVE',
      signature: json['signature'] ?? '',
      claimValue: json['claim_value'] ?? {},
    );
  }
}

class PendingActionItem {
  final String type;
  final String description;
  final String? deadline;
  final String? actionUrl;

  PendingActionItem({
    required this.type,
    required this.description,
    this.deadline,
    this.actionUrl,
  });

  factory PendingActionItem.fromJson(Map<String, dynamic> json) {
    return PendingActionItem(
      type: json['type'] ?? '',
      description: json['description'] ?? '',
      deadline: json['deadline'],
      actionUrl: json['action_url'],
    );
  }
}

class MoneyViewData {
  final String applicationId;
  final double sanctioned;
  final double credited;
  final double failed;
  final double pending;
  final List<Map<String, dynamic>> instalments;

  MoneyViewData({
    required this.applicationId,
    required this.sanctioned,
    required this.credited,
    required this.failed,
    required this.pending,
    required this.instalments,
  });

  factory MoneyViewData.fromJson(Map<String, dynamic> json) {
    return MoneyViewData(
      applicationId: json['application_id'] ?? '',
      sanctioned: (json['sanctioned'] as num?)?.toDouble() ?? 0.0,
      credited: (json['credited'] as num?)?.toDouble() ?? 0.0,
      failed: (json['failed'] as num?)?.toDouble() ?? 0.0,
      pending: (json['pending'] as num?)?.toDouble() ?? 0.0,
      instalments: (json['instalments'] as List?)?.cast<Map<String, dynamic>>() ?? [],
    );
  }
}

class PathwayData {
  final String currentScheme;
  final String? currentState;
  final int ladderPosition;
  final String? nextEligible;
  final String? transitionTrigger;
  final bool preFilledAvailable;

  PathwayData({
    required this.currentScheme,
    this.currentState,
    required this.ladderPosition,
    this.nextEligible,
    this.transitionTrigger,
    required this.preFilledAvailable,
  });

  factory PathwayData.fromJson(Map<String, dynamic> json) {
    return PathwayData(
      currentScheme: json['current_scheme'] ?? 'PRE_MATRIC',
      currentState: json['current_state'],
      ladderPosition: json['ladder_position'] ?? 0,
      nextEligible: json['next_eligible'],
      transitionTrigger: json['transition_trigger'],
      preFilledAvailable: json['pre_filled_available'] ?? false,
    );
  }
}

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final List<String>? toolCalls;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.toolCalls,
  });
}
