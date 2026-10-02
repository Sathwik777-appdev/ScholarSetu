import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/repository.dart';
import '../i18n.dart';
import '../state/providers.dart';
import 'components.dart';
import 'digilocker_screen.dart';
import 'labels.dart';
import 'rights_screens.dart';
import 'theme.dart';
import 'widgets.dart';

/// The next step for an application, in the app's language (the server's text is English).
String nextActionText(String state, String? serverText) {
  const steps = {
    'DRAFT': ('Review the pre-filled application and submit it', 'पहले से भरा आवेदन देखें और जमा करें'),
    'SUBMITTED': ('Waiting for your institute to start checking', 'आपके संस्थान की जाँच शुरू होने की प्रतीक्षा'),
    'INSTITUTE_VERIFICATION': ('Your institute is checking your application', 'आपका संस्थान आपका आवेदन जाँच रहा है'),
    'RESUBMITTED': ('Your institute will re-check your reply', 'आपका संस्थान आपका जवाब फिर से जाँचेगा'),
    'AUTHORITY_VERIFICATION': ('The district/state office is checking your application', 'ज़िला/राज्य कार्यालय आपका आवेदन जाँच रहा है'),
    'SANCTIONED': ('Sanctioned: the money will be sent to your bank account', 'स्वीकृत: पैसा आपके बैंक खाते में भेजा जाएगा'),
    'PAYMENT_INITIATED': ('The payment is on its way to your bank', 'भुगतान आपके बैंक की ओर भेजा गया है'),
    'PAYMENT_FAILED': ('Payment failed: open Money to fix it', 'भुगतान विफल: ठीक करने के लिए "पैसा" खोलें'),
    'RENEWAL_DUE': ('Renew your scholarship for the next year', 'अगले वर्ष के लिए छात्रवृत्ति का नवीनीकरण करें'),
    'REJECTED': ("Rejected: contact your institute's scholarship cell", 'अस्वीकृत: अपने संस्थान के छात्रवृत्ति प्रकोष्ठ से संपर्क करें'),
  };
  if (state == 'DEFICIENCY_RAISED') return t('Fix what the office asked for', 'कार्यालय ने जो माँगा है वह ठीक करें');
  final pair = steps[state];
  return pair == null ? (serverText ?? '') : t(pair.$1, pair.$2);
}

/// A ledger event, in words.
String eventText(String type) {
  const events = {
    'ApplicationCreated': ('Application created', 'आवेदन बनाया गया'),
    'ApplicationSubmitted': ('Application submitted', 'आवेदन जमा हुआ'),
    'InstituteVerificationStarted': ('Your institute started checking', 'संस्थान ने जाँच शुरू की'),
    'AuthorityVerificationStarted': ('Sent to the district/state office', 'ज़िला/राज्य कार्यालय को भेजा गया'),
    'DeficiencyRaised': ('The office asked you to fix something', 'कार्यालय ने कुछ ठीक करने को कहा'),
    'DeficiencyResponded': ('You replied', 'आपने जवाब दिया'),
    'Resubmitted': ('Sent back to your institute', 'संस्थान को वापस भेजा गया'),
    'Sanctioned': ('Scholarship sanctioned', 'छात्रवृत्ति स्वीकृत'),
    'Rejected': ('Application rejected', 'आवेदन अस्वीकृत'),
    'PaymentInitiated': ('Payment sent to the bank', 'भुगतान बैंक को भेजा गया'),
    'PaymentCredited': ('Money credited', 'पैसा खाते में आया'),
    'PaymentFailed': ('Payment failed', 'भुगतान विफल'),
    'ReviewCaseOpened': ('An officer will check a detail', 'एक अधिकारी एक जानकारी जाँचेगा'),
    'ReviewDecisionRecorded': ('An officer checked a detail', 'एक अधिकारी ने जानकारी जाँची'),
    'ScholarshipSurrendered': ('Scholarship given up for another', 'दूसरी के लिए छात्रवृत्ति छोड़ी गई'),
    'OneSchemeRuleAcknowledged': ('You confirmed the one-scholarship rule', 'आपने एक-छात्रवृत्ति नियम स्वीकार किया'),
    'SLABreached': ('Taking longer than the target; escalated', 'तय समय से ज़्यादा लगा; ऊपर भेजा गया'),
    'RenewalDue': ('Renewal due', 'नवीनीकरण बाकी'),
  };
  final pair = events[type];
  return pair == null ? humanize(type) : t(pair.$1, pair.$2);
}

// ── home ───────────────────────────────────────────────────────────────────

class StudentHomeTab extends ConsumerWidget {
  const StudentHomeTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final outbox = ref.watch(outboxProvider);
    final queuedApplications =
        outbox.items.where((i) => i.status == 'PENDING' && i.action == OutboxActions.createApplication).toList();
    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(outboxProvider.notifier).syncNow();
        for (final p in [dashboardProvider, pendingActionsProvider, pathwayProvider, passportProvider]) {
          ref.invalidate(p);
        }
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          CachedView(
            provider: dashboardProvider,
            builder: (context, data) {
              final apps = (data['applications'] as List).cast<Map<String, dynamic>>();
              final submitted = apps.where((a) => a['current_state'] != 'DRAFT').toList();
              return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Reveal(child: HeroHeader(
                  title: '${t('Hello', 'नमस्ते')}, ${(data['student']['name'] as String).split(' ').first}',
                  subtitle: submitted.isEmpty
                      ? t("Let's get your scholarship started.", 'चलिए आपकी छात्रवृत्ति शुरू करते हैं।')
                      : t('Here is where your scholarships stand.', 'आपकी छात्रवृत्तियाँ अभी यहाँ हैं।'),
                  image: 'assets/images/badge.webp',
                  imageSize: 96,
                  trailing: Figure(label: t('Received so far', 'अब तक मिला'), value: rupees(data['total_received'] as num),
                      color: Colors.white),
                )),
                const SizedBox(height: 12),
                _Journey(dashboard: data as Map<String, dynamic>),
                if (queuedApplications.isNotEmpty)
                  Card(
                    color: Colors.amber.shade50,
                    child: ListTile(
                      leading: const Icon(Icons.schedule),
                      title: Text(t('Application saved on this phone — NOT submitted yet', 'आवेदन इस फ़ोन पर सहेजा है — अभी जमा नहीं हुआ')),
                      subtitle: Text(t('It will be sent when the connection returns. Until then the office has not received it.',
                          'कनेक्शन आने पर यह भेजा जाएगा। तब तक कार्यालय को यह नहीं मिला है।')),
                    ),
                  ),
                Section(t('Your applications', 'आपके आवेदन')),
                if (apps.isEmpty) Text(t('No applications yet.', 'अभी कोई आवेदन नहीं।')),
                for (final (i, a) in apps.indexed)
                  Reveal(index: i + 1, child: ApplicationCard(application: a)),
              ]);
            },
          ),
          Section(t('Things you need to do', 'आपको ये करने हैं')),
          CachedView(
            provider: pendingActionsProvider,
            builder: (context, data) {
              final actions = (data as List).cast<Map<String, dynamic>>();
              if (actions.isEmpty) return Text(t('Nothing right now.', 'अभी कुछ नहीं।'));
              return Column(children: [
                for (final a in actions)
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.assignment_late_outlined, color: AppColors.saffron),
                      title: Text(a['description'] as String),
                      subtitle: a['deadline'] == null ? null : Text('${t('By', 'अंतिम तिथि')} ${dateIso(a['deadline'] as String)}'),
                      trailing: a['type'] == 'DEFICIENCY'
                          ? FilledButton.tonal(
                              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                                  builder: (_) => RespondScreen(
                                      applicationId: a['application_id'] as String,
                                      deficiencyId: a['reference_id'] as String,
                                      description: a['description'] as String))),
                              child: Text(t('Respond', 'जवाब दें')))
                          : null,
                    ),
                  ),
              ]);
            },
          ),
          Section(t('Your scholarship path', 'आपकी छात्रवृत्ति की राह')),
          CachedView(
            provider: pathwayProvider,
            builder: (context, data) => Text(data['next_eligible'] == null
                ? t('No next scheme is suggested yet.', 'अभी अगली योजना का सुझाव नहीं है।')
                : '${t('Next', 'अगली')}: ${schemeLabel(data['next_eligible'] as String)}'),
          ),
        ],
      ),
    );
  }
}

/// The three steps of a scholarship, with where the student stands: apply, verify details, get paid.
class _Journey extends ConsumerWidget {
  const _Journey({required this.dashboard});
  final Map<String, dynamic> dashboard;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final apps = (dashboard['applications'] as List).cast<Map<String, dynamic>>();
    final active = apps.where((a) => !['REJECTED', 'SURRENDERED', 'DRAFT'].contains(a['current_state'])).toList();
    final applied = active.isNotEmpty;
    final passport = ref.watch(passportProvider).value?.data as Map<String, dynamic>?;
    final verifiedCount = passport == null
        ? 0
        : (passport['attestations'] as Map).values.expand((v) => v as List).where((a) => a['status'] == 'ACTIVE').length;
    final paid = (dashboard['total_received'] as num) > 0;
    final target = active.isEmpty ? null : active.first['id'] as String;

    Widget step(int n, bool done, String title, String subtitle, {String? action, VoidCallback? onTap}) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            CircleAvatar(
              radius: 14,
              backgroundColor: done ? AppColors.teal : AppColors.line,
              child: done ? const Icon(Icons.check_rounded, size: 16, color: Colors.white)
                  : Text('$n', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.ink900)),
            ),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: TextStyle(fontWeight: FontWeight.w600, fontSize: 15,
                  color: done ? AppColors.muted : AppColors.text, decoration: done ? TextDecoration.lineThrough : null)),
              Text(subtitle, style: const TextStyle(fontSize: 13, color: AppColors.muted, height: 1.35)),
              if (!done && action != null && onTap != null)
                Padding(padding: const EdgeInsets.only(top: 6),
                    child: FilledButton(onPressed: onTap, style: FilledButton.styleFrom(visualDensity: VisualDensity.compact),
                        child: Text(action))),
            ])),
          ]),
        );

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(t('Your scholarship in 3 steps', '3 चरणों में आपकी छात्रवृत्ति'), style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          step(1, applied, t('Apply', 'आवेदन करें'),
              applied ? t('Your application is with the office.', 'आपका आवेदन कार्यालय के पास है।')
                  : t('Choose your scholarship and submit.', 'अपनी छात्रवृत्ति चुनें और जमा करें।'),
              action: t('Apply now', 'अभी आवेदन करें'),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => ApplyScreen(academicYear: dashboard['current_academic_year'] as String)))),
          step(2, verifiedCount > 0, t('Verify your details', 'अपनी जानकारी सत्यापित करें'),
              verifiedCount > 0
                  ? t('$verifiedCount detail(s) verified with government records.', '$verifiedCount जानकारी सरकारी रिकॉर्ड से सत्यापित।')
                  : t('One tap: we check with the offices, no uploads.', 'एक टैप: हम कार्यालयों से जाँचते हैं, कुछ अपलोड नहीं।'),
              action: t('Verify my details', 'मेरी जानकारी सत्यापित करें'),
              onTap: target == null ? null : () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => VerifyScreen(applicationId: target)))),
          step(3, paid, t('Get paid', 'पैसा पाएँ'),
              paid ? t('Money has reached your bank.', 'पैसा आपके बैंक में आ गया है।')
                  : t('Track every instalment in Money.', '"पैसा" में हर किस्त देखें।')),
        ]),
      ),
    );
  }
}

/// One application: scheme, stage pill, the six-step tracker and the next action, all from the ledger.
class ApplicationCard extends StatelessWidget {
  const ApplicationCard({super.key, required this.application});

  final Map<String, dynamic> application;

  @override
  Widget build(BuildContext context) {
    final a = application;
    final state = a['current_state'] as String;
    final next = nextActionText(state, a['next_action'] as String?);
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => ApplicationScreen(applicationId: a['id'] as String))),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(schemeLabel(a['scheme'] as String), style: Theme.of(context).textTheme.titleMedium)),
              Text(a['academic_year'] as String, style: const TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w500)),
            ]),
            const SizedBox(height: 2),
            Text(a['id'] as String, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5, color: AppColors.muted)),
            const SizedBox(height: 10),
            StatePill(state),
            const SizedBox(height: 16),
            StageTracker(state),
            if (next.isNotEmpty) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(14)),
                child: Row(children: [
                  const Icon(Icons.arrow_forward_rounded, size: 18, color: AppColors.saffron),
                  const SizedBox(width: 8),
                  Expanded(child: Text(next, style: const TextStyle(fontSize: 14, height: 1.35))),
                ]),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

// ── apply (goes through the outbox, so it also works offline) ──────────────

class ApplyScreen extends ConsumerStatefulWidget {
  const ApplyScreen({super.key, required this.academicYear});

  final String academicYear;

  @override
  ConsumerState<ApplyScreen> createState() => _ApplyScreenState();
}

class _ApplyScreenState extends ConsumerState<ApplyScreen> {
  String _scheme = 'POST_MATRIC';
  bool _acknowledge = false;
  bool _busy = false;
  String? _outcome;
  bool _canAcknowledge = false;

  Future<void> _submit() async {
    setState(() => _busy = true);
    final repo = ref.read(servicesProvider).repo;
    final key = await repo.queueAction(OutboxActions.createApplication, {
      'scheme': _scheme,
      'academic_year': widget.academicYear,
      if (_acknowledge) 'acknowledge_one_scheme_rule': true,
    });
    final report = await ref.read(outboxProvider.notifier).syncNow();
    final row = ref.read(outboxProvider).items.where((i) => i.key == key).firstOrNull;
    setState(() {
      _busy = false;
      if (row == null || row.status == 'PENDING') {
        _outcome = report.offline
            ? t('Saved on this phone. NOT submitted yet: it will be sent when the connection returns.',
                'इस फ़ोन पर सहेजा गया। अभी जमा नहीं हुआ: कनेक्शन आने पर भेजा जाएगा।')
            : t('Saved on this phone. NOT submitted yet: the server could not take it right now; it will be retried.',
                'इस फ़ोन पर सहेजा गया। अभी जमा नहीं हुआ: सर्वर अभी नहीं ले सका; फिर से भेजा जाएगा।');
      } else if (row.status == 'DONE') {
        _outcome = t('Submitted. Application ${row.result?['id']} is now with your institute.',
            'जमा हो गया। आवेदन ${row.result?['id']} अब आपके संस्थान के पास है।');
        ref.invalidate(dashboardProvider);
      } else {
        _outcome = '${t('Not submitted', 'जमा नहीं हुआ')}: ${row.lastError}';
        _canAcknowledge = (row.lastError ?? '').contains('surrender');
        ref.read(outboxProvider.notifier).dismiss(key);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(t('Apply', 'आवेदन करें'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('${t('Academic year', 'शैक्षणिक वर्ष')} ${widget.academicYear}', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        CachedView(
          provider: pathwayProvider,
          builder: (context, data) => data['next_eligible'] == null
              ? const SizedBox.shrink()
              : Text('${t('Suggested for you', 'आपके लिए सुझाव')}: ${schemeLabel(data['next_eligible'] as String)}'),
        ),
        RadioGroup<String>(
          groupValue: _scheme,
          onChanged: (v) => setState(() => _scheme = v ?? _scheme),
          child: Column(children: [
            for (final s in schemeLabels.entries) RadioListTile<String>(value: s.key, title: Text(s.value)),
          ]),
        ),
        if (_canAcknowledge)
          CheckboxListTile(
            value: _acknowledge,
            onChanged: (v) => setState(() => _acknowledge = v ?? false),
            title: Text(t('I understand I must give up my current scholarship if this one is sanctioned.',
                'मैं समझता/समझती हूँ कि यह स्वीकृत होने पर मुझे अपनी मौजूदा छात्रवृत्ति छोड़नी होगी।')),
          ),
        const SizedBox(height: 8),
        SizedBox(
          height: 52,
          child: FilledButton(onPressed: _busy ? null : _submit,
              child: Text(_busy ? t('Sending…', 'भेज रहे हैं…') : t('Submit application', 'आवेदन जमा करें'))),
        ),
        if (_outcome != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(_outcome!)),
      ]),
    );
  }
}

// ── deficiency response with an optional document (both queued) ───────────

class RespondScreen extends ConsumerStatefulWidget {
  const RespondScreen({super.key, required this.applicationId, required this.deficiencyId, required this.description});

  final String applicationId;
  final String deficiencyId;
  final String description;

  @override
  ConsumerState<RespondScreen> createState() => _RespondScreenState();
}

class _RespondScreenState extends ConsumerState<RespondScreen> {
  final _text = TextEditingController();
  String? _fileName;
  Uint8List? _fileBytes;
  bool _busy = false;

  Future<void> _pick() async {
    final picked = await FilePicker.pickFile(type: FileType.custom, allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png']);
    if (picked == null) return;
    final bytes = await picked.readAsBytes();
    setState(() {
      _fileName = picked.name;
      _fileBytes = bytes;
    });
  }

  Future<void> _send() async {
    if (_text.text.trim().isEmpty) {
      showMessage(context, t('Write a short reply.', 'एक छोटा जवाब लिखें।'));
      return;
    }
    setState(() => _busy = true);
    final repo = ref.read(servicesProvider).repo;
    final documents = <String>[];
    if (_fileBytes != null) {
      final title = 'Reply to: ${widget.description}';
      documents.add(await repo.queueUpload('DEFICIENCY_EVIDENCE', title.length > 120 ? title.substring(0, 120) : title,
          _fileName ?? 'document', _fileBytes!));
    }
    await repo.queueAction(OutboxActions.respondDeficiency, {
      'application_id': widget.applicationId,
      'deficiency_id': widget.deficiencyId,
      'response_text': _text.text.trim(),
      'document_ids': documents,
    });
    final report = await ref.read(outboxProvider.notifier).syncNow();
    if (!mounted) return;
    showMessage(context, report.offline
        ? t('Saved on this phone. It has NOT been sent yet; it will go when the connection returns.',
            'इस फ़ोन पर सहेजा गया। अभी भेजा नहीं गया; कनेक्शन आने पर जाएगा।')
        : report.refused > 0
            ? t('The server refused it. Open Sync to see why.', 'सर्वर ने अस्वीकार किया। कारण के लिए सिंक खोलें।')
            : t('Sent to the office.', 'कार्यालय को भेज दिया गया।'));
    ref.invalidate(pendingActionsProvider);
    ref.invalidate(dashboardProvider);
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(t('Respond', 'जवाब दें'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(widget.description, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        TextField(controller: _text, maxLines: 4, maxLength: 2000,
            decoration: InputDecoration(labelText: t('Your reply', 'आपका जवाब'), border: const OutlineInputBorder())),
        OutlinedButton.icon(onPressed: _pick, icon: const Icon(Icons.attach_file),
            label: Text(_fileName ?? t('Attach a document (PDF or photo)', 'दस्तावेज़ जोड़ें (PDF या फ़ोटो)'))),
        const SizedBox(height: 16),
        SizedBox(height: 52, child: FilledButton(onPressed: _busy ? null : _send,
            child: Text(_busy ? t('Saving…', 'सहेज रहे हैं…') : t('Send reply', 'जवाब भेजें')))),
        const SizedBox(height: 8),
        Text(t('If you are offline, your reply and document are kept (encrypted) on this phone and sent later.',
                'ऑफ़लाइन होने पर आपका जवाब और दस्तावेज़ इस फ़ोन पर (एन्क्रिप्टेड) रखे जाते हैं और बाद में भेजे जाते हैं।'),
            style: const TextStyle(fontSize: 13, color: AppColors.muted)),
      ]),
    );
  }
}

// ── one application: its ledger timeline, from events synced to this phone ─

final _eventsProvider = FutureProvider.family<List<Map<String, dynamic>>, String>(
    (ref, id) => ref.read(servicesProvider).db.eventsFor(id));

class ApplicationScreen extends ConsumerWidget {
  const ApplicationScreen({super.key, required this.applicationId});

  final String applicationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final events = ref.watch(_eventsProvider(applicationId));
    final lastSync = ref.watch(outboxProvider).lastSync;
    return Scaffold(
      appBar: AppBar(title: Text(applicationId)),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(outboxProvider.notifier).syncNow();
          ref.invalidate(_eventsProvider(applicationId));
        },
        child: events.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ErrorBox(message: errorText(e)),
          data: (list) => ListView(padding: const EdgeInsets.all(16), children: [
            if (ref.watch(sessionProvider).user?.role == 'STUDENT') ...[
              SizedBox(
                height: 52,
                child: FilledButton.icon(
                  onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => VerifyScreen(applicationId: applicationId))),
                  icon: const Icon(Icons.verified_user_outlined),
                  label: Text(t('Verify my details', 'मेरी जानकारी सत्यापित करें')),
                ),
              ),
              const SizedBox(height: 12),
            ],
            Text(lastSync == null
                    ? t('Not synced yet. Pull down to sync.', 'अभी सिंक नहीं हुआ। सिंक के लिए नीचे खींचें।')
                    : '${t('Updated', 'अपडेट')} ${when(lastSync)}',
                style: const TextStyle(fontSize: 13, color: AppColors.muted)),
            Section(t('What happened', 'क्या-क्या हुआ')),
            if (list.isEmpty) Text(t('No events on this phone yet.', 'इस फ़ोन पर अभी कोई जानकारी नहीं।')),
            for (final e in list.reversed)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.circle, size: 12, color: AppColors.saffron),
                title: Text(eventText(e['type'] as String), style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text('${whenIso(e['occurred_at'] as String)}\n'
                    '${t('Tamper-proof record', 'सुरक्षित रिकॉर्ड')} ${(e['hash'] as String).substring(0, 12)}…'),
                isThreeLine: true,
              ),
          ]),
        ),
      ),
    );
  }
}

// ── money, passport, alerts ───────────────────────────────────────────────

class MoneyTab extends ConsumerWidget {
  const MoneyTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(outboxProvider.notifier).syncNow();
        ref.invalidate(paymentsProvider);
      },
      child: ListView(padding: const EdgeInsets.all(16), children: [
        CachedView(
          provider: paymentsProvider,
          builder: (context, data) {
            final apps = (data['applications'] as List).cast<Map<String, dynamic>>();
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Reveal(child: HeroHeader(
                title: rupees(data['total_credited'] as num),
                subtitle: t('credited to your bank, of ${rupees(data['total_sanctioned'] as num)} sanctioned',
                    '${rupees(data['total_sanctioned'] as num)} स्वीकृत में से आपके बैंक में आया'),
                image: 'assets/images/coins.webp',
                imageSize: 104,
                trailing: Wrap(spacing: 20, runSpacing: 8, children: [
                  Figure(label: t('On the way', 'रास्ते में'), value: rupees(data['total_pending'] as num), color: Colors.white),
                  if ((data['total_failed'] as num) > 0)
                    Figure(label: t('Failed', 'विफल'), value: rupees(data['total_failed'] as num), color: const Color(0xFFFDA4AF)),
                ]),
              )),
              if (apps.isEmpty)
                Padding(padding: const EdgeInsets.only(top: 12), child: Text(t('Nothing sanctioned yet.', 'अभी कुछ स्वीकृत नहीं।'))),
              for (final a in apps) ...[
                Section('${schemeLabel(a['scheme'] as String)} ${a['academic_year']}'),
                if ((a['instalments'] as List).isEmpty)
                  Text('${t('Status', 'स्थिति')}: ${stateLabel(a['state'] as String)}', style: const TextStyle(color: AppColors.muted)),
                for (final i in (a['instalments'] as List).cast<Map<String, dynamic>>())
                  _InstalmentTile(i, applicationId: a['application_id'] as String),
              ],
            ]);
          },
        ),
      ]),
    );
  }
}

/// Where a wallet document came from, as the server labels it. "Verified" only when the issuer signed it.
String documentSourceText(Map<String, dynamic> d) {
  final label = (d['source_label'] as String?)?.isNotEmpty == true ? d['source_label'] as String : '${d['source']}';
  if (d['verified'] == true) return 'From $label · issuer-signed';
  if (d['test_document'] == true) return 'From $label · test data, not verified';
  return '$label · not verified';
}

/// The same, in the app's language.
String documentSourceLabel(Map<String, dynamic> d) {
  final label = (d['source_label'] as String?)?.isNotEmpty == true ? d['source_label'] as String : '${d['source']}';
  final shown = d['source'] == 'UPLOAD' ? t('Uploaded by you', 'आपने अपलोड किया') : label;
  if (d['verified'] == true) return '$shown · ${t('issuer-signed', 'जारीकर्ता द्वारा हस्ताक्षरित')}';
  if (d['test_document'] == true) return '$shown · ${t('test data, not verified', 'परीक्षण डेटा, सत्यापित नहीं')}';
  return '$shown · ${t('not verified', 'सत्यापित नहीं')}';
}

class PassportTab extends ConsumerWidget {
  const PassportTab({super.key});

  Future<void> _upload(BuildContext context, WidgetRef ref) async {
    final file = await FilePicker.pickFile(type: FileType.custom, allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png']);
    if (file == null) return;
    final name = file.name.length < 3 ? 'Document ${file.name}' : file.name;
    await ref.read(servicesProvider).repo.queueUpload('OTHER', name, file.name, await file.readAsBytes());
    final report = await ref.read(outboxProvider.notifier).syncNow();
    ref.invalidate(walletProvider);
    if (context.mounted) {
      showMessage(context, report.offline
          ? t('Saved on this phone; it will upload when you are online.', 'इस फ़ोन पर सहेजा; ऑनलाइन होने पर अपलोड होगा।')
          : t('Uploaded.', 'अपलोड हो गया।'));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(outboxProvider.notifier).syncNow();
        ref.invalidate(passportProvider);
        ref.invalidate(walletProvider);
      },
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Reveal(child: HeroHeader(
          title: t('Scholarship Passport', 'छात्रवृत्ति पासपोर्ट'),
          subtitle: t('Verified details are confirmed by the issuing office and signed by ScholarSetu. Reuse them for every scholarship.',
              'सत्यापित जानकारी जारी करने वाले कार्यालय से पुष्ट और ScholarSetu द्वारा हस्ताक्षरित है। हर छात्रवृत्ति में इसका उपयोग करें।'),
          image: 'assets/images/badge.webp',
          imageSize: 100,
        )),
        CachedView(
          provider: passportProvider,
          builder: (context, data) {
            final groups = (data['attestations'] as Map<String, dynamic>);
            if (groups.isEmpty) {
              return Padding(padding: const EdgeInsets.only(top: 8),
                  child: Text(t('Nothing verified yet. Open an application and tap "Verify my details".',
                      'अभी कुछ सत्यापित नहीं। कोई आवेदन खोलें और "मेरी जानकारी सत्यापित करें" दबाएँ।')));
            }
            return Column(children: [
              for (final entry in groups.entries)
                for (final a in (entry.value as List).cast<Map<String, dynamic>>())
                  Card(
                    child: ListTile(
                      leading: Icon(a['status'] == 'ACTIVE' ? Icons.verified : Icons.hourglass_bottom,
                          color: a['status'] == 'ACTIVE' ? AppColors.teal : AppColors.saffron),
                      title: Text(claimLabel(entry.key), style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text('${stateLabel(a['status'] as String)} · ${t('from', 'स्रोत')} ${sourceLabel(a['source'] as String?)}'
                          '${a['expiry_date'] == null ? '' : ' · ${t('valid until', 'मान्य')} ${dateIso(a['expiry_date'] as String)}'}'
                          '${a['status'] == 'ACTIVE' && a['signature'] != null ? '\n${t('Tap to show its QR code', 'QR कोड देखने के लिए टैप करें')}' : ''}'),
                      onTap: a['status'] == 'ACTIVE' && a['signature'] != null
                          ? () => showPassportQr(context, claimLabel(entry.key), a['signature'] as String)
                          : null,
                    ),
                  ),
            ]);
          },
        ),
        Section(t('Documents', 'दस्तावेज़')),
        CachedView(
          provider: walletProvider,
          builder: (context, data) {
            final docs = (data['documents'] as List).cast<Map<String, dynamic>>();
            return Column(children: [
              if (docs.isEmpty) Text(t('No documents yet.', 'अभी कोई दस्तावेज़ नहीं।')),
              for (final d in docs)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(d['verified'] == true ? Icons.verified_outlined : Icons.description_outlined,
                      color: d['test_document'] == true ? Colors.orange.shade800 : null),
                  title: Text(d['title'] as String),
                  subtitle: Text(documentSourceLabel(d)),
                ),
            ]);
          },
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 52,
          child: FilledButton.icon(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DigiLockerScreen())),
              icon: const Icon(Icons.cloud_download_outlined),
              label: Text(t('Get from DigiLocker', 'DigiLocker से लाएँ'))),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(onPressed: () => _upload(context, ref), icon: const Icon(Icons.upload_file),
            label: Text(t('Upload a document', 'दस्तावेज़ अपलोड करें'))),
      ]),
    );
  }
}

class AlertsTab extends ConsumerWidget {
  const AlertsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(outboxProvider.notifier).syncNow();
        ref.invalidate(notificationsProvider);
      },
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Text(t('Checked every minute while the app is open.', 'ऐप खुला रहने पर हर मिनट जाँचा जाता है।'),
            style: const TextStyle(fontSize: 13, color: AppColors.muted)),
        CachedView(
          provider: notificationsProvider,
          builder: (context, data) {
            final items = (data as List).cast<Map<String, dynamic>>();
            if (items.isEmpty) {
              return Padding(padding: const EdgeInsets.only(top: 8), child: Text(t('No messages.', 'कोई संदेश नहीं।')));
            }
            return Column(children: [
              for (final n in items)
                Card(
                  child: ListTile(
                    leading: Icon(n['read_at'] == null ? Icons.mark_email_unread_outlined : Icons.drafts_outlined,
                        color: n['read_at'] == null ? AppColors.saffron : AppColors.muted),
                    title: Text(n['body'] as String),
                    subtitle: Text(whenIso(n['created_at'] as String)),
                    onTap: n['read_at'] != null
                        ? null
                        : () async {
                            await ref.read(servicesProvider).repo.queueAction(
                                OutboxActions.markNotificationRead, {'notification_id': n['id']});
                            await ref.read(outboxProvider.notifier).syncNow();
                            ref.invalidate(notificationsProvider);
                          },
                  ),
                ),
            ]);
          },
        ),
      ]),
    );
  }
}

class _InstalmentTile extends StatelessWidget {
  const _InstalmentTile(this.i, {required this.applicationId});

  final Map<String, dynamic> i;
  final String applicationId;

  @override
  Widget build(BuildContext context) {
    final state = i['state'] as String;
    final color = state == 'CREDITED' ? AppColors.teal : state == 'FAILED' ? AppColors.rose : AppColors.saffron;
    final icon = state == 'CREDITED' ? Icons.check_rounded : state == 'FAILED' ? Icons.close_rounded : Icons.schedule_rounded;
    return Card(
      child: ListTile(
        leading: CircleAvatar(backgroundColor: color.withValues(alpha: 0.12), child: Icon(icon, color: color)),
        title: Text(i['description'] as String, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(stateLabel(state) +
            (i['failure_code'] == null ? '' : ' · ${t('tap to fix', 'ठीक करने के लिए टैप करें')}') +
            (i['credited_at'] == null ? '' : ' · ${dateIso(i['credited_at'] as String)}')),
        trailing: Text(rupees(i['amount'] as num),
            style: const TextStyle(fontWeight: FontWeight.w700, fontFeatures: [FontFeature.tabularFigures()])),
        onTap: state != 'FAILED'
            ? null
            : () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => BankFixScreen(applicationId: applicationId, paymentId: i['payment_id'] as String))),
      ),
    );
  }
}
