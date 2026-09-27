import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Thrown when the SQLite library is not SQLCipher. The app then refuses to store anything locally
/// rather than silently writing an unencrypted file.
class EncryptionUnavailable implements Exception {
  @override
  String toString() => 'The encrypted local store (SQLCipher) is not available on this device.';
}

const _schema = [
  '''CREATE TABLE IF NOT EXISTS cache (
       key TEXT PRIMARY KEY, body TEXT NOT NULL, updated_at INTEGER NOT NULL)''',
  '''CREATE TABLE IF NOT EXISTS events (
       event_id TEXT PRIMARY KEY, position INTEGER NOT NULL UNIQUE, application_id TEXT NOT NULL,
       type TEXT NOT NULL, occurred_at TEXT NOT NULL, actor TEXT NOT NULL, source TEXT NOT NULL,
       payload TEXT NOT NULL, hash TEXT NOT NULL, hash_prev TEXT NOT NULL)''',
  'CREATE INDEX IF NOT EXISTS events_app ON events(application_id, position)',
  '''CREATE TABLE IF NOT EXISTS applications (
       id TEXT PRIMARY KEY, body TEXT NOT NULL, updated_at INTEGER NOT NULL)''',
  // The persistent outbox. `kind` is 'action' (sent in a /v1/sync/outbox batch) or 'upload'
  // (a wallet document, sent as multipart with an Idempotency-Key). Files stay inside this encrypted DB.
  '''CREATE TABLE IF NOT EXISTS outbox (
       idempotency_key TEXT PRIMARY KEY, kind TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL,
       file_name TEXT, file_bytes BLOB, created_at INTEGER NOT NULL, status TEXT NOT NULL,
       attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, result TEXT)''',
  'CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
];

class CacheEntry {
  CacheEntry(this.body, this.updatedAt);
  final dynamic body;
  final DateTime updatedAt;
}

class OutboxRow {
  OutboxRow(this.key, this.kind, this.action, this.payload, this.fileName, this.fileBytes, this.createdAt,
      this.status, this.attempts, this.lastError, this.result);

  final String key;
  final String kind;
  final String action;
  final Map<String, dynamic> payload;
  final String? fileName;
  final Uint8List? fileBytes;
  final DateTime createdAt;
  final String status; // PENDING | DONE | REJECTED
  final int attempts;
  final String? lastError;
  final Map<String, dynamic>? result;
}

/// Drift database used through SQL statements (no generated code), encrypted with SQLCipher.
class LocalDb extends GeneratedDatabase {
  LocalDb._(super.executor);

  /// The SQLCipher version reported by the library; shown to the user as proof of encryption.
  late final String cipherVersion;

  @override
  Iterable<TableInfo<Table, Object?>> get allTables => const [];

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) async {
          for (final statement in _schema) {
            await customStatement(statement);
          }
        },
      );

  static Future<LocalDb> open(String hexKey) async {
    final dir = await getApplicationSupportDirectory();
    final file = File(p.join(dir.path, 'scholarsetu.db'));
    return openFile(file, hexKey);
  }

  static Future<LocalDb> openFile(File file, String hexKey) async {
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(hexKey)) throw ArgumentError('bad key');
    final executor = NativeDatabase(file, setup: (db) {
      final version = db.select('PRAGMA cipher_version;');
      if (version.isEmpty || (version.first.values.first ?? '').toString().isEmpty) {
        throw EncryptionUnavailable();
      }
      db.execute("PRAGMA key = \"x'$hexKey'\";");
      db.select('SELECT count(*) FROM sqlite_master;'); // fails here if the key is wrong
    });
    final db = LocalDb._(executor);
    final rows = await db.customSelect('PRAGMA cipher_version;').get();
    final version = rows.isEmpty ? '' : (rows.first.data.values.first ?? '').toString();
    if (version.isEmpty) {
      await db.close();
      throw EncryptionUnavailable();
    }
    db.cipherVersion = version;
    return db;
  }

  // ── cache ────────────────────────────────────────────────────────────────

  Future<void> putCache(String key, dynamic body) => customStatement(
      'INSERT OR REPLACE INTO cache(key, body, updated_at) VALUES (?, ?, ?)',
      [key, jsonEncode(body), DateTime.now().millisecondsSinceEpoch]);

  Future<CacheEntry?> getCache(String key) async {
    final rows = await customSelect('SELECT body, updated_at FROM cache WHERE key = ?',
        variables: [Variable.withString(key)]).get();
    if (rows.isEmpty) return null;
    return CacheEntry(jsonDecode(rows.first.read<String>('body')),
        DateTime.fromMillisecondsSinceEpoch(rows.first.read<int>('updated_at')));
  }

  // ── synced ledger events ─────────────────────────────────────────────────

  Future<void> saveSyncPage(List<dynamic> events, List<dynamic> applications, int cursor) async {
    await transaction(() async {
      for (final e in events) {
        await customStatement(
            'INSERT OR IGNORE INTO events(event_id, position, application_id, type, occurred_at, actor, source, '
            'payload, hash, hash_prev) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [e['event_id'], e['position'], e['application_id'], e['type'], e['occurred_at'], e['actor'],
             e['source'], jsonEncode(e['payload']), e['hash'], e['hash_prev']]);
      }
      final now = DateTime.now().millisecondsSinceEpoch;
      for (final a in applications) {
        await customStatement('INSERT OR REPLACE INTO applications(id, body, updated_at) VALUES (?, ?, ?)',
            [a['id'], jsonEncode(a), now]);
      }
      await setValue('sync_cursor', '$cursor');
      await setValue('last_sync', DateTime.now().toIso8601String());
    });
  }

  Future<List<Map<String, dynamic>>> eventsFor(String applicationId) async {
    final rows = await customSelect(
        'SELECT * FROM events WHERE application_id = ? ORDER BY position',
        variables: [Variable.withString(applicationId)]).get();
    return rows
        .map((r) => {
              'event_id': r.read<String>('event_id'),
              'position': r.read<int>('position'),
              'type': r.read<String>('type'),
              'occurred_at': r.read<String>('occurred_at'),
              'actor': r.read<String>('actor'),
              'source': r.read<String>('source'),
              'payload': jsonDecode(r.read<String>('payload')),
              'hash': r.read<String>('hash'),
              'hash_prev': r.read<String>('hash_prev'),
            })
        .toList();
  }

  Future<Map<String, dynamic>?> application(String id) async {
    final rows = await customSelect('SELECT body FROM applications WHERE id = ?',
        variables: [Variable.withString(id)]).get();
    return rows.isEmpty ? null : jsonDecode(rows.first.read<String>('body')) as Map<String, dynamic>;
  }

  // ── outbox ───────────────────────────────────────────────────────────────

  Future<void> enqueue({required String key, required String kind, required String action,
      required Map<String, dynamic> payload, String? fileName, Uint8List? fileBytes}) {
    return customStatement(
        'INSERT INTO outbox(idempotency_key, kind, action, payload, file_name, file_bytes, created_at, status) '
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')",
        [key, kind, action, jsonEncode(payload), fileName, fileBytes, DateTime.now().millisecondsSinceEpoch]);
  }

  Future<List<OutboxRow>> outbox({String? status}) async {
    final rows = await customSelect(
        'SELECT * FROM outbox ${status == null ? '' : 'WHERE status = ?'} ORDER BY created_at, rowid',
        variables: [if (status != null) Variable.withString(status)]).get();
    return rows.map((r) {
      final result = r.readNullable<String>('result');
      return OutboxRow(
        r.read<String>('idempotency_key'), r.read<String>('kind'), r.read<String>('action'),
        jsonDecode(r.read<String>('payload')) as Map<String, dynamic>, r.readNullable<String>('file_name'),
        r.readNullable<Uint8List>('file_bytes'), DateTime.fromMillisecondsSinceEpoch(r.read<int>('created_at')),
        r.read<String>('status'), r.read<int>('attempts'), r.readNullable<String>('last_error'),
        result == null ? null : jsonDecode(result) as Map<String, dynamic>,
      );
    }).toList();
  }

  Future<void> markOutbox(String key, String status, {Object? result, String? error}) => customStatement(
      'UPDATE outbox SET status = ?, result = ?, last_error = ?, file_bytes = CASE WHEN ? = \'DONE\' '
      'THEN NULL ELSE file_bytes END WHERE idempotency_key = ?',
      [status, result == null ? null : jsonEncode(result), error, status, key]);

  Future<void> countAttempt(String key, String error) => customStatement(
      'UPDATE outbox SET attempts = attempts + 1, last_error = ? WHERE idempotency_key = ?', [error, key]);

  Future<void> dismissOutbox(String key) =>
      customStatement("DELETE FROM outbox WHERE idempotency_key = ? AND status <> 'PENDING'", [key]);

  // ── key/value ────────────────────────────────────────────────────────────

  Future<void> setValue(String key, String value) =>
      customStatement('INSERT OR REPLACE INTO kv(key, value) VALUES (?, ?)', [key, value]);

  Future<String?> value(String key) async {
    final rows = await customSelect('SELECT value FROM kv WHERE key = ?', variables: [Variable.withString(key)]).get();
    return rows.isEmpty ? null : rows.first.read<String>('value');
  }

  /// Signing out wipes everything saved for the previous user.
  Future<void> wipe() async {
    for (final table in ['cache', 'events', 'applications', 'outbox', 'kv']) {
      await customStatement('DELETE FROM $table');
    }
  }
}
