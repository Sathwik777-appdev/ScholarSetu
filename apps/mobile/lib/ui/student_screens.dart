import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/repository.dart';
import '../state/providers.dart';
import 'components.dart';
import 'labels.dart';
import 'theme.dart';
import 'widgets.dart';

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
        ref.invalidate(dashboardProvider);
        ref.invalidate(pendingActionsProvider);
        ref.invalidate(pathwayProvider);
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
                  title: 'Hello, ${(data['student']['name'] as String).split(' ').first}',
                  subtitle: submitted.isEmpty ? 'Let\'s get your scholarship started.' : 'Here is where your scholarships stand.',
                  image: 'assets/images/badge.webp',
                  imageSize: 96,
                  trailing: Figure(label: 'Received so far', value: rupees(data['total_received'] as num), color: Colors.white),
                )),
                if (queuedApplications.isNotEmpty)
                  Card(
                    color: Colors.amber.shade50,
                    child: const ListTile(
                      leading: Icon(Icons.schedule),
                      title: Text('Application saved on this phone — NOT submitted yet'),
                      subtitle: Text('It will be sent when the connection returns. Until then the office has not received it.'),
                    ),
                  )
                else if (submitted.isEmpty)
                  Card(
                    color: Colors.orange.shade50,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Registered — application NOT submitted',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.orange.shade900)),
                        const SizedBox(height: 4),
                        const Text('You have an account, but you have not applied for any scholarship yet.'),
                        const SizedBox(height: 8),
                        FilledButton(
                          onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                              builder: (_) => ApplyScreen(academicYear: data['current_academic_year'] as String))),
                          child: const Text('Continue your application'),
                        ),
                      ]),
                    ),
                  ),
                const Section('Your applications'),
                if (apps.isEmpty) const Text('No applications yet.'),
                for (final (i, a) in apps.indexed)
                  Reveal(index: i + 1, child: ApplicationCard(application: a)),
              ]);
            },
          ),
          const Section('Things you need to do'),
          CachedView(
            provider: pendingActionsProvider,
            builder: (context, data) {
              final actions = (data as List).cast<Map<String, dynamic>>();
              if (actions.isEmpty) return const Text('Nothing right now.');
              return Column(children: [
                for (final a in actions)
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.assignment_late_outlined),
                      title: Text(a['description'] as String),
                      subtitle: a['deadline'] == null ? null : Text('By ${whenIso(a['deadline'] as String)}'),
                      trailing: a['type'] == 'DEFICIENCY'
                          ? TextButton(
                              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                                  builder: (_) => RespondScreen(
                                      applicationId: a['application_id'] as String,
                                      deficiencyId: a['reference_id'] as String,
                                      description: a['description'] as String))),
                              child: const Text('Respond'))
                          : null,
                    ),
                  ),
              ]);
            },
          ),
          const Section('Your scholarship path'),
          CachedView(
            provider: pathwayProvider,
            builder: (context, data) => Text(data['next_eligible'] == null
                ? 'No next scheme is suggested yet.'
                : 'Next: ${schemeLabel(data['next_eligible'] as String)}'
                    '${data['transition_trigger'] == null ? '' : ' — ${data['transition_trigger']}'}'),
          ),
        ],
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
              Text(a['academic_year'] as String, style: const TextStyle(fontSize: 12.5, color: AppColors.muted, fontWeight: FontWeight.w500)),
            ]),
            const SizedBox(height: 2),
            Text(a['id'] as String, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, color: AppColors.muted)),
            const SizedBox(height: 10),
            StatePill(state),
            const SizedBox(height: 16),
            StageTracker(state),
            if ((a['next_action'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(14)),
                child: Row(children: [
                  const Icon(Icons.arrow_forward_rounded, size: 18, color: AppColors.saffron),
                  const SizedBox(width: 8),
                  Expanded(child: Text(a['next_action'] as String, style: const TextStyle(fontSize: 13.5, height: 1.35))),
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
            ? 'Saved on this phone. NOT submitted yet: it will be sent when the connection returns.'
            : 'Saved on this phone. NOT submitted yet: the server could not take it right now; it will be retried.';
      } else if (row.status == 'DONE') {
        _outcome = 'Submitted. Application ${row.result?['id']} is now with your institute.';
        ref.invalidate(dashboardProvider);
      } else {
        _outcome = 'Not submitted: ${row.lastError}';
        _canAcknowledge = (row.lastError ?? '').contains('surrender');
        ref.read(outboxProvider.notifier).dismiss(key);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Apply')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Academic year ${widget.academicYear}'),
        const SizedBox(height: 8),
        CachedView(
          provider: pathwayProvider,
          builder: (context, data) => data['next_eligible'] == null
              ? const SizedBox.shrink()
              : Text('Suggested for you: ${schemeLabel(data['next_eligible'] as String)}'),
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
            title: const Text('I understand I must give up my current scholarship if this one is sanctioned.'),
          ),
        FilledButton(onPressed: _busy ? null : _submit, child: Text(_busy ? 'Sending…' : 'Submit application')),
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
      showMessage(context, 'Write a short reply.');
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
        ? 'Saved on this phone. It has NOT been sent yet; it will go when the connection returns.'
        : report.refused > 0
            ? 'The server refused it. Open Sync to see why.'
            : 'Sent to the office.');
    ref.invalidate(pendingActionsProvider);
    ref.invalidate(dashboardProvider);
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Respond')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(widget.description, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        TextField(controller: _text, maxLines: 4, maxLength: 2000,
            decoration: const InputDecoration(labelText: 'Your reply', border: OutlineInputBorder())),
        OutlinedButton.icon(onPressed: _pick, icon: const Icon(Icons.attach_file),
            label: Text(_fileName ?? 'Attach a document (PDF or photo)')),
        const SizedBox(height: 16),
        FilledButton(onPressed: _busy ? null : _send, child: Text(_busy ? 'Saving…' : 'Send reply')),
        const SizedBox(height: 8),
        const Text('If you are offline, your reply and document are kept (encrypted) on this phone and sent later.',
            style: TextStyle(fontSize: 12)),
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
            Text(lastSync == null ? 'Not synced yet. Pull down to sync.' : 'Events synced up to ${when(lastSync)}.',
                style: const TextStyle(fontSize: 12)),
            if (list.isEmpty) const Padding(padding: EdgeInsets.only(top: 16), child: Text('No events on this phone yet.')),
            for (final e in list.reversed)
              ListTile(
                leading: const Icon(Icons.circle, size: 12),
                title: Text(humanize(e['type'] as String)),
                subtitle: Text('${whenIso(e['occurred_at'] as String)} · ${e['source']}\n'
                    'Record ${(e['hash'] as String).substring(0, 12)}…'),
                isThreeLine: true,
              ),
          ]),
        ),
      ),
    );
  }
}

// ── money, passport, alerts ───────────────────────────────────────────────

class MoneyTab extends StatelessWidget {
  const MoneyTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      CachedView(
        provider: paymentsProvider,
        builder: (context, data) {
          final apps = (data['applications'] as List).cast<Map<String, dynamic>>();
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Reveal(child: HeroHeader(
              title: rupees(data['total_credited'] as num),
              subtitle: 'credited to your bank, of ${rupees(data['total_sanctioned'] as num)} sanctioned',
              image: 'assets/images/coins.webp',
              imageSize: 104,
              trailing: Wrap(spacing: 20, runSpacing: 8, children: [
                Figure(label: 'On the way', value: rupees(data['total_pending'] as num), color: Colors.white),
                if ((data['total_failed'] as num) > 0)
                  Figure(label: 'Failed', value: rupees(data['total_failed'] as num), color: const Color(0xFFFDA4AF)),
              ]),
            )),
            if (apps.isEmpty) const Padding(padding: EdgeInsets.only(top: 12), child: Text('Nothing sanctioned yet.')),
            for (final a in apps) ...[
              Section('${schemeLabel(a['scheme'] as String)} ${a['academic_year']}'),
              for (final i in (a['instalments'] as List).cast<Map<String, dynamic>>())
                _InstalmentTile(i),
            ],
          ]);
        },
      ),
    ]);
  }
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
      showMessage(context, report.offline ? 'Saved on this phone; it will upload when you are online.' : 'Uploaded.');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Reveal(child: HeroHeader(
        title: 'Scholarship Passport',
        subtitle: 'Active items were confirmed by the issuing office and signed by ScholarSetu. '
            'Provisional ones are still being reviewed by an officer.',
        image: 'assets/images/badge.webp',
        imageSize: 100,
      )),
      CachedView(
        provider: passportProvider,
        builder: (context, data) {
          final groups = (data['attestations'] as Map<String, dynamic>);
          if (groups.isEmpty) return const Padding(padding: EdgeInsets.only(top: 8), child: Text('Nothing verified yet.'));
          return Column(children: [
            for (final entry in groups.entries)
              for (final a in (entry.value as List).cast<Map<String, dynamic>>())
                Card(
                  child: ListTile(
                    leading: Icon(a['status'] == 'ACTIVE' ? Icons.verified : Icons.hourglass_bottom,
                        color: a['status'] == 'ACTIVE' ? Colors.green.shade700 : Colors.orange.shade700),
                    title: Text(humanize(entry.key)),
                    subtitle: Text('${humanize(a['status'] as String)} · from ${a['source']}'
                        '${a['expiry_date'] == null ? '' : ' · valid until ${whenIso(a['expiry_date'] as String)}'}'),
                  ),
                ),
          ]);
        },
      ),
      const Section('Documents'),
      CachedView(
        provider: walletProvider,
        builder: (context, data) {
          final docs = (data['documents'] as List).cast<Map<String, dynamic>>();
          return Column(children: [
            if (docs.isEmpty) const Text('No documents yet.'),
            for (final d in docs)
              ListTile(
                leading: const Icon(Icons.description_outlined),
                title: Text(d['title'] as String),
                subtitle: Text(d['verified'] == true ? 'From ${d['source']} (issuer-signed)' : 'Uploaded by you (not verified)'),
              ),
          ]);
        },
      ),
      OutlinedButton.icon(onPressed: () => _upload(context, ref), icon: const Icon(Icons.upload_file),
          label: const Text('Upload a document')),
    ]);
  }
}

class AlertsTab extends ConsumerWidget {
  const AlertsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Text('Checked every minute while the app is open.', style: TextStyle(fontSize: 12)),
      CachedView(
        provider: notificationsProvider,
        builder: (context, data) {
          final items = (data as List).cast<Map<String, dynamic>>();
          if (items.isEmpty) return const Padding(padding: EdgeInsets.only(top: 8), child: Text('No messages.'));
          return Column(children: [
            for (final n in items)
              Card(
                child: ListTile(
                  leading: Icon(n['read_at'] == null ? Icons.mark_email_unread_outlined : Icons.drafts_outlined),
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
    ]);
  }
}

class _InstalmentTile extends StatelessWidget {
  const _InstalmentTile(this.i);

  final Map<String, dynamic> i;

  @override
  Widget build(BuildContext context) {
    final state = i['state'] as String;
    final color = state == 'CREDITED' ? AppColors.teal : state == 'FAILED' ? AppColors.rose : AppColors.saffron;
    final icon = state == 'CREDITED' ? Icons.check_rounded : state == 'FAILED' ? Icons.close_rounded : Icons.schedule_rounded;
    return Card(
      child: ListTile(
        leading: CircleAvatar(backgroundColor: color.withValues(alpha: 0.12), child: Icon(icon, color: color)),
        title: Text(i['description'] as String, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(humanize(state) +
            (i['failure_code'] == null ? '' : ' (${i['failure_code']})') +
            (i['credited_at'] == null ? '' : ' on ${whenIso(i['credited_at'] as String)}')),
        trailing: Text(rupees(i['amount'] as num),
            style: const TextStyle(fontWeight: FontWeight.w700, fontFeatures: [FontFeature.tabularFigures()])),
      ),
    );
  }
}
