import 'package:intl/intl.dart';

const stateLabels = {
  'DRAFT': 'Draft (not submitted)',
  'SUBMITTED': 'Submitted',
  'INSTITUTE_VERIFICATION': 'Being checked by your institute',
  'DEFICIENCY_RAISED': 'Action needed from you',
  'RESUBMITTED': 'Resubmitted',
  'AUTHORITY_VERIFICATION': 'Being checked by the district/state',
  'SANCTIONED': 'Sanctioned',
  'REJECTED': 'Rejected',
  'PAYMENT_INITIATED': 'Payment sent to bank',
  'CREDITED': 'Money credited',
  'PAYMENT_FAILED': 'Payment failed',
  'RENEWAL_DUE': 'Renewal due',
};

const schemeLabels = {
  'PRE_MATRIC': 'Pre-Matric',
  'POST_MATRIC': 'Post-Matric',
  'TOP_CLASS': 'Top Class Education',
  'NFST': 'National Fellowship (NFST)',
  'NOS': 'National Overseas (NOS)',
};

String stateLabel(String? s) => stateLabels[s] ?? (s ?? '');
String schemeLabel(String? s) => schemeLabels[s] ?? (s ?? '');

String humanize(String code) {
  final spaced = code.replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (m) => '${m[1]} ${m[2]}').replaceAll('_', ' ');
  return spaced.isEmpty ? spaced : spaced[0].toUpperCase() + spaced.substring(1).toLowerCase();
}

final _money = NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 0);
String rupees(num? v) => _money.format(v ?? 0);

final _when = DateFormat('d MMM yyyy, h:mm a');
String when(DateTime t) => _when.format(t.toLocal());
String whenIso(String? iso) => iso == null ? '' : when(DateTime.parse(iso));
