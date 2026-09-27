import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:drift/drift.dart' show driftRuntimeOptions;
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:scholarsetu_mobile/data/api.dart';
import 'package:scholarsetu_mobile/data/local_db.dart';
import 'package:scholarsetu_mobile/data/repository.dart';

const key1 = '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';
const key2 = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';

/// A fake ScholarSetu server that applies each idempotency key once, like the real one.
class FakeServer {
  bool online = true;
  final applied = <String, Map<String, dynamic>>{};
  final uploads = <String, Map<String, dynamic>>{};
  final requests = <String>[];

  http.Client get client => MockClient((req) async {
        if (!online) throw http.ClientException('network is unreachable');
        requests.add('${req.method} ${req.url.path}');
        if (req.url.path.endsWith('/me/wallet/documents')) {
          final k = req.headers['idempotency-key']!;
          final first = !uploads.containsKey(k);
          uploads.putIfAbsent(k, () => {'id': 'doc-${uploads.length + 1}'});
          return http.Response(jsonEncode(uploads[k]), first ? 201 : 200);
        }
        if (req.url.path.endsWith('/sync/outbox')) {
          final items = (jsonDecode(req.body)['items'] as List).cast<Map<String, dynamic>>();
          final results = items.map((i) {
            final k = i['idempotency_key'] as String;
            if (applied.containsKey(k)) {
              return {'idempotency_key': k, 'action': i['action'], 'status': 'DUPLICATE',
                      'original_status': 'APPLIED', 'http_status': 200, 'result': applied[k]};
            }
            if (i['payload']['application_id'] == 'NOT-MINE') {
              return {'idempotency_key': k, 'action': i['action'], 'status': 'REJECTED', 'http_status': 404,
                      'error': 'Application not found'};
            }
            applied[k] = {'event_id': 'evt-$k', 'payload': i['payload']};
            return {'idempotency_key': k, 'action': i['action'], 'status': 'APPLIED', 'http_status': 200,
                    'result': applied[k]};
          }).toList();
          return http.Response(jsonEncode({'results': results}), 200);
        }
        if (req.url.path.endsWith('/sync')) {
          return http.Response(jsonEncode({'events': [], 'applications': [], 'next_cursor': 0, 'has_more': false,
                                           'server_time': DateTime.now().toIso8601String()}), 200);
        }
        if (req.url.path.endsWith('/me/dashboard')) return http.Response(jsonEncode({'ok': true}), 200);
        return http.Response('{"detail":"not found"}', 404);
      });
}

void main() {
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true; // the tests reopen the file to simulate restarts
  late Directory dir;
  late File file;

  setUp(() async {
    dir = await Directory.systemTemp.createTemp('scholarsetu_test');
    file = File('${dir.path}/test.db');
  });
  tearDown(() => dir.delete(recursive: true));

  test('the local database is SQLCipher-encrypted and needs the key', () async {
    final db = await LocalDb.openFile(file, key1);
    expect(db.cipherVersion, isNotEmpty);
    await db.putCache('dashboard', {'secret': 'Sunita Hansda'});
    await db.close();
    final raw = await file.readAsBytes();
    expect(utf8.decode(raw.sublist(0, 15), allowMalformed: true), isNot('SQLite format 3'));
    expect(latin1.decode(raw).contains('Sunita Hansda'), isFalse);
    final wrong = await LocalDb.openFile(file, key2).then((d) => d.getCache('dashboard')).then((_) => 'opened',
        onError: (_) => 'refused');
    expect(wrong, 'refused');
  });

  test('a queued action survives the app being killed and is sent once after reconnecting', () async {
    final server = FakeServer()..online = false;
    var db = await LocalDb.openFile(file, key1);
    var repo = Repository(Api('http://api/v1', client: server.client), db);
    await repo.queueAction(OutboxActions.respondDeficiency,
        {'application_id': 'APP-1', 'deficiency_id': 'D1', 'response_text': 'Uploaded', 'document_ids': <String>[]});
    final offline = await repo.sync();
    expect(offline.offline, isTrue);
    expect((await db.outbox(status: 'PENDING')).length, 1);
    await db.close(); // the app is killed

    server.online = true;
    db = await LocalDb.openFile(file, key1);
    repo = Repository(Api('http://api/v1', client: server.client), db);
    expect((await db.outbox(status: 'PENDING')).length, 1, reason: 'the queue must survive a restart');
    final report = await repo.sync();
    expect(report.sent, 1);
    expect(server.applied.length, 1);
    expect((await db.outbox(status: 'DONE')).length, 1);
    await repo.sync();
    expect(server.applied.length, 1, reason: 'nothing is sent twice');
    await db.close();
  });

  test('an offline upload is sent first and its id replaces the local reference', () async {
    final server = FakeServer();
    final db = await LocalDb.openFile(file, key1);
    final repo = Repository(Api('http://api/v1', client: server.client), db);
    final ref = await repo.queueUpload('INCOME_CERT', 'Income certificate', 'income.pdf', Uint8List.fromList([37, 80, 68, 70]));
    await repo.queueAction(OutboxActions.respondDeficiency,
        {'application_id': 'APP-1', 'deficiency_id': 'D1', 'response_text': 'See attached', 'document_ids': [ref]});
    await repo.sync();
    expect(server.requests.first, 'POST /v1/me/wallet/documents');
    final sent = server.applied.values.single['payload'] as Map<String, dynamic>;
    expect(sent['document_ids'], ['doc-1']);
    await db.close();
  });

  test('a refused action is kept as refused with the reason and does not block later ones', () async {
    final server = FakeServer();
    final db = await LocalDb.openFile(file, key1);
    final repo = Repository(Api('http://api/v1', client: server.client), db);
    await repo.queueAction(OutboxActions.submitApplication, {'application_id': 'NOT-MINE'});
    await repo.queueAction(OutboxActions.submitApplication, {'application_id': 'APP-2'});
    final report = await repo.sync();
    expect(report.refused, 1);
    expect(report.sent, 1);
    final refused = await db.outbox(status: 'REJECTED');
    expect(refused.single.lastError, 'Application not found');
    await db.close();
  });

  test('offline reads show the saved copy with its time; with no copy they fail', () async {
    final server = FakeServer();
    final db = await LocalDb.openFile(file, key1);
    final repo = Repository(Api('http://api/v1', client: server.client), db);
    final fresh = await repo.cached('dashboard', '/me/dashboard');
    expect(fresh.fromCache, isFalse);
    server.online = false;
    final saved = await repo.cached('dashboard', '/me/dashboard');
    expect(saved.fromCache, isTrue);
    expect(saved.data, {'ok': true});
    await expectLater(repo.cached('payments', '/me/payments'), throwsA(isA<OfflineException>()));
    await db.close();
  });
}
