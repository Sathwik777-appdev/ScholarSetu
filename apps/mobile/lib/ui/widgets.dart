import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api.dart';
import '../i18n.dart';
import '../data/repository.dart';
import '../state/providers.dart';
import 'labels.dart';
import 'server_sheet.dart';
import 'theme.dart';

/// Says what is actually happening: whether the server answered the last request, how many saved
/// changes are waiting, and what was refused. Hidden while online with nothing pending.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conn = ref.watch(connectionProvider);
    final outbox = ref.watch(outboxProvider);
    final lines = <String>[];
    Color color = Colors.amber.shade50;
    if (conn.reachable == false) {
      lines.add(t('No connection to ScholarSetu since ${when(conn.since!)}. You are seeing information saved on this phone.',
          '${when(conn.since!)} से ScholarSetu से कनेक्शन नहीं है। आप इस फ़ोन पर सहेजी जानकारी देख रहे हैं।'));
    }
    if (outbox.pending > 0) {
      lines.add(conn.reachable == false
          ? t('${outbox.pending} change(s) saved on this phone will be sent when the connection returns. '
              'They have NOT reached the office yet.',
              'इस फ़ोन पर सहेजे ${outbox.pending} बदलाव कनेक्शन आने पर भेजे जाएँगे। वे अभी कार्यालय तक नहीं पहुँचे हैं।')
          : t('${outbox.pending} saved change(s) waiting to be sent.', '${outbox.pending} सहेजे बदलाव भेजे जाने बाकी हैं।'));
    }
    if (outbox.refused.isNotEmpty) {
      color = Colors.red.shade50;
      lines.add(t('${outbox.refused.length} saved change(s) were refused by the server. Open "Sync" to see why.',
          'सर्वर ने ${outbox.refused.length} सहेजे बदलाव अस्वीकार किए। कारण देखने के लिए "सिंक" खोलें।'));
    }
    if (lines.isEmpty) return const SizedBox.shrink();
    final problem = outbox.refused.isNotEmpty;
    return AnimatedSize(
      duration: const Duration(milliseconds: 250),
      child: Container(
        margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: problem ? Colors.red.shade200 : Colors.amber.shade300),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(conn.reachable == false ? Icons.cloud_off_rounded : problem ? Icons.error_outline : Icons.sync_rounded,
              size: 20, color: problem ? Colors.red.shade800 : Colors.brown.shade700),
          const SizedBox(width: 10),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [for (final l in lines) Padding(padding: const EdgeInsets.only(bottom: 2),
                child: Text(l, style: const TextStyle(fontSize: 13, height: 1.35)))],
          )),
        ]),
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
      loading: () => const _Skeleton(),
      error: (e, _) => ErrorBox(
        message: e is OfflineException
            ? t('No connection, and nothing has been saved on this phone yet. Connect once to load your information.',
                'कनेक्शन नहीं है और इस फ़ोन पर अभी कुछ सहेजा नहीं गया। अपनी जानकारी लाने के लिए एक बार कनेक्ट करें।')
            : e.toString(),
        onRetry: () => ref.invalidate(provider),
      ),
      data: (cached) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (cached.fromCache)
            Align(
              alignment: Alignment.centerLeft,
              child: Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: Colors.amber.shade50, borderRadius: BorderRadius.circular(99),
                    border: Border.all(color: Colors.amber.shade200)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.history_rounded, size: 14, color: Colors.brown.shade700),
                  const SizedBox(width: 6),
                  Text('${t('Saved copy. Last updated', 'सहेजी प्रति। अंतिम अपडेट')} ${when(cached.updatedAt)}',
                      style: TextStyle(color: Colors.brown.shade800, fontSize: 12, fontWeight: FontWeight.w500)),
                ]),
              ),
            ),
          builder(context, cached.data),
        ],
      ),
    );
  }
}

class ErrorBox extends ConsumerWidget {
  const ErrorBox({super.key, required this.message, this.onRetry, this.onConfigureServer});

  final String message;
  final VoidCallback? onRetry;
  final VoidCallback? onConfigureServer;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isConnectionError = message.toLowerCase().contains('connection') ||
        message.toLowerCase().contains('scholarsetu');
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.red.shade100),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(Icons.error_outline_rounded, color: Colors.red.shade700),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(message, style: TextStyle(color: Colors.red.shade900, height: 1.35)),
              if (onRetry != null || onConfigureServer != null || isConnectionError)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      if (onRetry != null)
                        TextButton(
                          style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            visualDensity: VisualDensity.compact,
                          ),
                          onPressed: onRetry,
                          child: Text(t('Try again', 'फिर से कोशिश करें')),
                        ),
                      if (onConfigureServer != null || isConnectionError)
                        OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            visualDensity: VisualDensity.compact,
                            backgroundColor: Colors.white,
                            side: BorderSide(color: Colors.red.shade200),
                          ),
                          icon: const Icon(Icons.settings_ethernet_rounded, size: 14, color: AppColors.ink900),
                          label: Text(
                            t('Server settings', 'सर्वर सेटिंग'),
                            style: const TextStyle(fontSize: 12, color: AppColors.ink900, fontWeight: FontWeight.w600),
                          ),
                          onPressed: onConfigureServer ?? () => showServerConfigSheet(context, ref),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ]),
    );
  }
}

class Section extends StatelessWidget {
  const Section(this.title, {super.key});

  final String title;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 22, bottom: 10),
        child: Text(title.toUpperCase(),
            style: const TextStyle(fontSize: 12, letterSpacing: 0.8, fontWeight: FontWeight.w600, color: Color(0xFF64748B))),
      );
}

void showMessage(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

String errorText(Object e) {
  if (e is ApiException && e.code == 'WAKING') {
    return t('ScholarSetu is starting up after being idle. This takes a few minutes; please try again shortly.',
        'ScholarSetu कुछ देर बंद रहने के बाद शुरू हो रहा है। इसमें कुछ मिनट लगते हैं; थोड़ी देर बाद फिर कोशिश करें।');
  }
  return e is ApiException || e is OfflineException ? e.toString() : t('Something went wrong.', 'कुछ गड़बड़ हो गई।');
}

class _Skeleton extends StatefulWidget {
  const _Skeleton();

  @override
  State<_Skeleton> createState() => _SkeletonState();
}

class _SkeletonState extends State<_Skeleton> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))
    ..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: t('Loading', 'लोड हो रहा है'),
      child: FadeTransition(
        opacity: Tween(begin: 0.45, end: 1.0).animate(_c),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (final w in [0.5, 1.0, 0.8])
            Container(
              margin: const EdgeInsets.symmetric(vertical: 6),
              height: w == 1.0 ? 84 : 16,
              width: MediaQuery.of(context).size.width * w,
              decoration: BoxDecoration(color: const Color(0xFFE8ECF4), borderRadius: BorderRadius.circular(12)),
            ),
        ]),
      ),
    );
  }
}
