import 'dart:typed_data';

import 'package:uuid/uuid.dart';

import 'api.dart';
import 'local_db.dart';

/// Data shown on screen, with where it came from. `fromCache` is true when the server could not be
/// reached and this is the copy saved on the phone at `updatedAt`.
class Cached<T> {
  Cached(this.data, this.updatedAt, {this.fromCache = false});

  final T data;
  final DateTime updatedAt;
  final bool fromCache;
}

class SyncReport {
  SyncReport({this.sent = 0, this.refused = 0, this.received = 0, this.offline = false});

  final int sent;
  final int refused;
  final int received;
  final bool offline;
}

/// Outbox actions the server accepts in POST /v1/sync/outbox.
class OutboxActions {
  static const createApplication = 'CREATE_APPLICATION';
  static const submitApplication = 'SUBMIT_APPLICATION';
  static const respondDeficiency = 'RESPOND_DEFICIENCY';
  static const markNotificationRead = 'MARK_NOTIFICATION_READ';
  static const uploadDocument = 'UPLOAD_DOCUMENT';
}

/// A document id that refers to an upload still waiting in the outbox; replaced by the real id once sent.
String localDocumentRef(String uploadKey) => 'local:$uploadKey';

class Repository {
  Repository(this.api, this.db);

  final Api api;
  final LocalDb db;
  static const _uuid = Uuid();
  bool _syncing = false;

  /// GET from the API and keep a copy. When the server cannot be reached (or fails), return the saved
  /// copy with its time; with no copy, the error goes to the screen. Never invents data.
  Future<Cached<dynamic>> cached(String cacheKey, String path, {Map<String, String>? query}) async {
    try {
      final body = await api.get(path, query: query);
      await db.putCache(cacheKey, body);
      return Cached(body, DateTime.now());
    } on OfflineException {
      final entry = await db.getCache(cacheKey);
      if (entry == null) rethrow;
      return Cached(entry.body, entry.updatedAt, fromCache: true);
    } on ApiException catch (e) {
      if (e.status < 500) rethrow;
      final entry = await db.getCache(cacheKey);
      if (entry == null) rethrow;
      return Cached(entry.body, entry.updatedAt, fromCache: true);
    }
  }

  // ── outbox ───────────────────────────────────────────────────────────────

  Future<String> queueAction(String action, Map<String, dynamic> payload) async {
    final key = 'act-${_uuid.v4()}';
    await db.enqueue(key: key, kind: 'action', action: action, payload: payload);
    return key;
  }

  /// Queue a wallet upload. Returns a reference usable in a queued deficiency response's document_ids.
  Future<String> queueUpload(String documentType, String title, String fileName, Uint8List bytes) async {
    final key = 'upl-${_uuid.v4()}';
    await db.enqueue(key: key, kind: 'upload', action: OutboxActions.uploadDocument,
        payload: {'document_type': documentType, 'title': title}, fileName: fileName, fileBytes: bytes);
    return localDocumentRef(key);
  }

  /// Send queued items in the order they were made. Stops at the first item that cannot be sent yet
  /// (offline or a temporary server error), so later items never overtake earlier ones.
  Future<SyncReport> drainOutbox() async {
    var sent = 0, refused = 0;
    final pending = await db.outbox(status: 'PENDING');
    var i = 0;
    while (i < pending.length) {
      final item = pending[i];
      if (item.kind == 'upload') {
        try {
          final doc = await api.upload('/me/wallet/documents', item.payload.map((k, v) => MapEntry(k, '$v')),
              item.fileBytes ?? Uint8List(0), item.fileName ?? 'document', idempotencyKey: item.key);
          await db.markOutbox(item.key, 'DONE', result: doc);
          sent++;
        } on OfflineException {
          return SyncReport(sent: sent, refused: refused, offline: true);
        } on ApiException catch (e) {
          if (!e.isPermanent) {
            await db.countAttempt(item.key, e.message);
            return SyncReport(sent: sent, refused: refused);
          }
          await db.markOutbox(item.key, 'REJECTED', error: e.message);
          refused++;
        }
        i++;
        continue;
      }
      // A run of consecutive actions goes in one batch (the server applies them in order).
      final batch = <OutboxRow>[];
      while (i < pending.length && pending[i].kind == 'action' && batch.length < 50) {
        batch.add(pending[i]);
        i++;
      }
      final items = <Map<String, dynamic>>[];
      for (final row in batch) {
        final resolved = await _resolveDocumentRefs(row);
        if (resolved == null) {
          await db.markOutbox(row.key, 'REJECTED', error: 'The attached document was refused, so this was not sent.');
          refused++;
          continue;
        }
        items.add({'idempotency_key': row.key, 'action': row.action, 'payload': resolved,
                   'created_at': row.createdAt.toUtc().toIso8601String()});
      }
      if (items.isEmpty) continue;
      try {
        final response = await api.post('/sync/outbox', {'items': items});
        for (final r in (response['results'] as List)) {
          final key = r['idempotency_key'] as String;
          final status = r['status'] as String;
          final outcome = status == 'DUPLICATE' ? r['original_status'] as String : status;
          if (outcome == 'APPLIED') {
            await db.markOutbox(key, 'DONE', result: r['result']);
            sent++;
          } else if (outcome == 'REJECTED') {
            await db.markOutbox(key, 'REJECTED', error: _errorText(r['error']));
            refused++;
          } else {
            await db.countAttempt(key, _errorText(r['error']));
            return SyncReport(sent: sent, refused: refused);
          }
        }
      } on OfflineException {
        return SyncReport(sent: sent, refused: refused, offline: true);
      } on ApiException catch (e) {
        for (final row in batch) {
          await db.countAttempt(row.key, e.message);
        }
        return SyncReport(sent: sent, refused: refused);
      }
    }
    return SyncReport(sent: sent, refused: refused);
  }

  /// Replace `local:<upload key>` document references with the uploaded document's id.
  /// Returns null if a referenced upload was refused. Pending uploads are sent first (drain order).
  Future<Map<String, dynamic>?> _resolveDocumentRefs(OutboxRow row) async {
    final ids = row.payload['document_ids'];
    if (ids is! List) return row.payload;
    final done = {for (final r in await db.outbox()) r.key: r};
    final resolved = <String>[];
    for (final id in ids.cast<String>()) {
      if (!id.startsWith('local:')) {
        resolved.add(id);
        continue;
      }
      final upload = done[id.substring(6)];
      if (upload == null || upload.status != 'DONE' || upload.result == null) return null;
      resolved.add(upload.result!['id'] as String);
    }
    return {...row.payload, 'document_ids': resolved};
  }

  static String _errorText(dynamic error) {
    if (error is String) return error;
    if (error is Map && error['message'] is String) return error['message'] as String;
    if (error is List && error.isNotEmpty && error.first is Map) return '${error.first['msg']}';
    return 'Refused by the server';
  }

  // ── delta sync ───────────────────────────────────────────────────────────

  /// Send the outbox, then fetch every ledger event after the saved cursor.
  Future<SyncReport> sync() async {
    if (_syncing) return SyncReport();
    _syncing = true;
    try {
      final out = await drainOutbox();
      if (out.offline) return out;
      var received = 0;
      var cursor = int.tryParse(await db.value('sync_cursor') ?? '') ?? 0;
      while (true) {
        final page = await api.get('/sync', query: {'cursor': '$cursor', 'limit': '200'});
        final events = page['events'] as List;
        cursor = page['next_cursor'] as int;
        await db.saveSyncPage(events, page['applications'] as List, cursor);
        received += events.length;
        if (page['has_more'] != true) break;
      }
      return SyncReport(sent: out.sent, refused: out.refused, received: received);
    } on OfflineException {
      return SyncReport(offline: true);
    } finally {
      _syncing = false;
    }
  }

  Future<DateTime?> lastSync() async {
    final v = await db.value('last_sync');
    return v == null ? null : DateTime.tryParse(v);
  }
}
