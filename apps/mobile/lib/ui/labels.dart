import 'package:intl/intl.dart';

import '../i18n.dart';

const _stateLabels = {
  'DRAFT': ('Draft (not submitted)', 'ड्राफ़्ट (जमा नहीं हुआ)'),
  'SUBMITTED': ('Submitted', 'जमा हो गया'),
  'INSTITUTE_VERIFICATION': ('Being checked by your institute', 'आपका संस्थान जाँच कर रहा है'),
  'DEFICIENCY_RAISED': ('Action needed from you', 'आपको कुछ करना है'),
  'RESUBMITTED': ('Resubmitted', 'दोबारा जमा हुआ'),
  'AUTHORITY_VERIFICATION': ('Being checked by the district/state', 'ज़िला/राज्य जाँच कर रहा है'),
  'SANCTIONED': ('Sanctioned', 'स्वीकृत'),
  'REJECTED': ('Rejected', 'अस्वीकृत'),
  'PAYMENT_INITIATED': ('Payment sent to bank', 'भुगतान बैंक को भेजा गया'),
  'CREDITED': ('Money credited', 'पैसा खाते में आ गया'),
  'PAYMENT_FAILED': ('Payment failed', 'भुगतान विफल'),
  'RENEWAL_DUE': ('Renewal due', 'नवीनीकरण बाकी'),
  'SURRENDERED': ('Surrendered (another scholarship taken)', 'छोड़ा गया (दूसरी छात्रवृत्ति ली)'),
  'SCHEDULED': ('Scheduled', 'तय'),
  'INITIATED': ('Sent to bank', 'बैंक को भेजा गया'),
  'RETRYING': ('Sent again', 'फिर से भेजा गया'),
  'FAILED': ('Failed', 'विफल'),
  'CANCELLED': ('Cancelled', 'रद्द'),
  'ACTIVE': ('Verified', 'सत्यापित'),
  'PROVISIONAL': ('Waiting for an officer', 'अधिकारी की प्रतीक्षा'),
  'REVOKED': ('Withdrawn', 'वापस लिया गया'),
  'EXPIRED': ('Expired', 'समाप्त'),
};

const _schemeLabels = {
  'PRE_MATRIC': ('Pre-Matric', 'प्री-मैट्रिक'),
  'POST_MATRIC': ('Post-Matric', 'पोस्ट-मैट्रिक'),
  'TOP_CLASS': ('Top Class Education', 'टॉप क्लास शिक्षा'),
  'NFST': ('National Fellowship (NFST)', 'राष्ट्रीय फ़ेलोशिप (NFST)'),
  'NOS': ('National Overseas (NOS)', 'राष्ट्रीय विदेश छात्रवृत्ति (NOS)'),
};

const _claimLabels = {
  'IDENTITY': ('Identity', 'पहचान'),
  'ST_STATUS': ('Scheduled Tribe certificate', 'अनुसूचित जनजाति प्रमाणपत्र'),
  'INCOME': ('Family income', 'परिवार की आय'),
  'DOMICILE': ('Domicile', 'निवास'),
  'SCHOOL_ENROLMENT': ('School enrolment', 'स्कूल में नामांकन'),
  'HIGHER_ED': ('College enrolment', 'कॉलेज में नामांकन'),
  'ACADEMIC_RECORDS': ('Marksheets', 'अंकपत्र'),
  'NET_JRF': ('UGC-NET / JRF', 'UGC-NET / JRF'),
  'DISABILITY': ('Disability certificate', 'दिव्यांगता प्रमाणपत्र'),
  'TOP_CLASS_INSTITUTION': ('Top-class institution admission', 'टॉप क्लास संस्थान में प्रवेश'),
  'FOREIGN_ADMISSION': ('Admission abroad', 'विदेश में प्रवेश'),
};

String _pick((String, String)? pair, String fallback) => pair == null ? fallback : t(pair.$1, pair.$2);

String stateLabel(String? s) => _pick(_stateLabels[s], humanize(s ?? ''));
String schemeLabel(String? s) => _pick(_schemeLabels[s], s ?? '');
String claimLabel(String? s) => _pick(_claimLabels[s], humanize(s ?? ''));
Map<String, String> get schemeLabels => {for (final k in _schemeLabels.keys) k: schemeLabel(k)};

/// Who confirmed something, in plain words (an officer's internal id is never shown).
String sourceLabel(String? source) {
  if (source == null || source.isEmpty) return '';
  if (source.startsWith('OFFICER:')) return t('An officer', 'एक अधिकारी');
  return source;
}

String humanize(String code) {
  final spaced = code.replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (m) => '${m[1]} ${m[2]}').replaceAll('_', ' ');
  return spaced.isEmpty ? spaced : spaced[0].toUpperCase() + spaced.substring(1).toLowerCase();
}

final _money = NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 0);
String rupees(num? v) => _money.format(v ?? 0);

String when(DateTime t0) => DateFormat('d MMM yyyy, h:mm a', isHindi ? 'hi' : 'en').format(t0.toLocal());
String whenIso(String? iso) => iso == null ? '' : when(DateTime.parse(iso));
String dateIso(String? iso) => iso == null ? '' : DateFormat('d MMM yyyy', isHindi ? 'hi' : 'en').format(DateTime.parse(iso).toLocal());

const _actionLabels = {
  'CREATE_APPLICATION': ('Apply for a scholarship', 'छात्रवृत्ति के लिए आवेदन'),
  'SUBMIT_APPLICATION': ('Submit an application', 'आवेदन जमा करना'),
  'RESPOND_DEFICIENCY': ('Reply to the office', 'कार्यालय को जवाब'),
  'MARK_NOTIFICATION_READ': ('Mark a message read', 'संदेश पढ़ा गया'),
  'UPLOAD_DOCUMENT': ('Upload a document', 'दस्तावेज़ अपलोड'),
};

/// A saved offline action, in words.
String actionLabel(String action) => _pick(_actionLabels[action], humanize(action));
