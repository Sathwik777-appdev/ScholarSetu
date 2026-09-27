import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../data/repository.dart';
import '../state/providers.dart';
import 'labels.dart';

/// Says what is actually happening: whether the server answered the last request, how many saved
/// changes are waiting, and what was refused. Hidden while online with nothing pending.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conn = ref.watch(connectionProvider);
    final outbox = ref.watch(outboxProvider);
    final lines = <String>[];
    Color color = Colors.amber.shade100;
    if (conn.reachable == false) {
      lines.add('No connection to ScholarSetu since ${when(conn.since!)}. '
          'You are seeing information saved on this phone.');
    }
    if (outbox.pending > 0) {
      lines.add(conn.reachable == false
          ? '${outbox.pending} change(s) saved on this phone will be sent when the connection returns. '
              'They have NOT reached the office yet.'
          : '${outbox.pending} saved change(s) waiting to be sent.');
    }
    if (outbox.refused.isNotEmpty) {
      color = Colors.red.shade100;
      lines.add('${outbox.refused.length} saved change(s) were refused by the server. Open "Sync" to see why.');
    }
    if (lines.isEmpty) return const SizedBox.shrink();
    return Material(
      color: color,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [for (final l in lines) Text(l, style: const TextStyle(fontSize: 13))],
        ),
      ),
    );
  }
}

/// Shows a cached read model: a "Last updated" line when the data is the phone's saved copy, a clear
/// error when there is nothing to show, and a spinner while loading.
class CachedView extends ConsumerWidget {
  const CachedView({super.key, required this.provider, required this.builder});

  final FutureProvider<Cached<dynamic>> provider;
  final Widget Function(BuildContext context, dynamic data) builder;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(provider);
    return value.when(
      loading: () => const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
      error: (e, _) => ErrorBox(
        message: e is OfflineException
            ? 'No connection, and nothing has been saved on this phone yet. Connect once to load your information.'
            : e.toString(),
        onRetry: () => ref.invalidate(provider),
      ),
      data: (cached) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (cached.fromCache)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text('Saved copy. Last updated ${when(cached.updatedAt)}',
                  style: TextStyle(color: Colors.brown.shade700, fontSize: 12, fontStyle: FontStyle.italic)),
            ),
          builder(context, cached.data),
        ],
      ),
    );
  }
}

class ErrorBox extends StatelessWidget {
  const ErrorBox({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(message, style: TextStyle(color: Colors.red.shade900)),
          if (onRetry != null) TextButton(onPressed: onRetry, child: const Text('Try again')),
        ]),
      ),
    );
  }
}

class Section extends StatelessWidget {
  const Section(this.title, {super.key});

  final String title;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 16, bottom: 8),
        child: Text(title, style: Theme.of(context).textTheme.titleMedium),
      );
}

void showMessage(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

String errorText(Object e) => e is ApiException || e is OfflineException ? e.toString() : 'Something went wrong.';
