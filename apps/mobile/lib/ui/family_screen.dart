import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/providers.dart';
import 'home_screen.dart';
import 'labels.dart';
import 'student_screens.dart';
import 'widgets.dart';

/// Family mode: a parent or guardian sees every child in the household, read-only.
class FamilyScreen extends ConsumerWidget {
  const FamilyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Family'), actions: const [SyncButton(), AccountMenu()]),
      body: Column(children: [
        const OfflineBanner(),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async {
              await ref.read(outboxProvider.notifier).syncNow();
              ref.invalidate(householdProvider);
            },
            child: ListView(padding: const EdgeInsets.all(16), children: [
              CachedView(
                provider: householdProvider,
                builder: (context, data) {
                  final children = (data['students'] as List).cast<Map<String, dynamic>>();
                  return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    Text(data['guardian_name'] as String, style: Theme.of(context).textTheme.headlineSmall),
                    for (final child in children) ...[
                      Section(child['student']['name'] as String),
                      if ((child['applications'] as List).isEmpty)
                        const Text('Registered — application NOT submitted.'),
                      for (final a in (child['applications'] as List).cast<Map<String, dynamic>>())
                        Card(
                          child: ListTile(
                            title: Text('${schemeLabel(a['scheme'] as String)} ${a['academic_year']}'),
                            subtitle: Text('${stateLabel(a['current_state'] as String)}\n${a['next_action'] ?? ''}'),
                            isThreeLine: true,
                            onTap: () => Navigator.of(context).push(MaterialPageRoute(
                                builder: (_) => ApplicationScreen(applicationId: a['id'] as String))),
                          ),
                        ),
                      Text('Received: ${rupees(child['total_received'] as num)}'),
                    ],
                  ]);
                },
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}
