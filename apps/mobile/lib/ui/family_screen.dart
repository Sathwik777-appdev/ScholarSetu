import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n.dart';
import '../state/providers.dart';
import 'home_screen.dart';
import 'components.dart';
import 'labels.dart';
import 'student_screens.dart';
import 'widgets.dart';

/// Family mode: a parent or guardian sees every child in the household, read-only.
class FamilyScreen extends ConsumerWidget {
  const FamilyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: Text(t('Family', 'परिवार')), actions: const [SyncButton(), AccountMenu()]),
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
                    HeroHeader(
                      title: data['guardian_name'] as String,
                      subtitle: t('${children.length} ${children.length == 1 ? 'child' : 'children'} · family view (read-only)',
                          '${children.length} बच्चे · परिवार दृश्य (केवल देखने के लिए)'),
                      image: 'assets/images/badge.webp',
                      imageSize: 88,
                    ),
                    for (final child in children) ...[
                      Section(child['student']['name'] as String),
                      if ((child['applications'] as List).isEmpty)
                        Text(t('Registered — application NOT submitted.', 'पंजीकृत — आवेदन जमा नहीं हुआ।')),
                      for (final a in (child['applications'] as List).cast<Map<String, dynamic>>())
                        ApplicationCard(application: a),
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text('${t('Received so far', 'अब तक मिला')}: ${rupees(child['total_received'] as num)}',
                            style: const TextStyle(fontWeight: FontWeight.w600)),
                      ),
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
