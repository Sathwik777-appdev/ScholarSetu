import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config.dart';
import '../data/api.dart';
import '../data/local_db.dart';
import '../data/repository.dart';
import '../data/secure_store.dart';

/// Created in main() once the encrypted database is open, and injected with overrideWithValue.
class Services {
  Services(this.api, this.db, this.secure) : repo = Repository(api, db);

  final Api api;
  final LocalDb db;
  final SecureStore secure;
  final Repository repo;

  Future<void> updateApiUrl(String newOrigin) async {
    final cleanOrigin = formatOrigin(newOrigin);
    api.baseUrl = formatBaseUrl(cleanOrigin);
    await secure.setApiUrl(cleanOrigin);
  }
}

class ApiOriginNotifier extends Notifier<String> {
  @override
  String build() => defaultApiOrigin;

  void setOrigin(String origin) => state = origin;
}

final currentApiOriginProvider = NotifierProvider<ApiOriginNotifier, String>(ApiOriginNotifier.new);

final servicesProvider = Provider<Services>((ref) => throw UnimplementedError('overridden in main()'));

// ── session ────────────────────────────────────────────────────────────────

class SessionUser {
  SessionUser.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        name = j['name'] as String,
        role = j['role'] as String,
        studentId = j['student_id'] as String?,
        householdId = j['household_id'] as String?;

  final String id;
  final String name;
  final String role; // STUDENT | GUARDIAN | MITRA
  final String? studentId;
  final String? householdId;
}

const appRoles = {'STUDENT', 'GUARDIAN', 'MITRA'};

class SessionState {
  const SessionState({this.user, this.checking = false});

  final SessionUser? user;
  final bool checking;
}

class SessionNotifier extends Notifier<SessionState> {
  Services get _s => ref.read(servicesProvider);

  @override
  SessionState build() {
    _s.api.onUnauthorized = () => signOut();
    Future.microtask(_restore);
    return const SessionState(checking: true);
  }

  Future<void> _restore() async {
    final token = await _s.secure.token();
    if (token == null) {
      state = const SessionState();
      return;
    }
    _s.api.token = token;
    try {
      final me = await _s.api.get('/auth/me') as Map<String, dynamic>;
      await _s.db.putCache('me', me);
      state = SessionState(user: SessionUser.fromJson(me));
    } on OfflineException {
      // Offline start: use the saved profile; the server re-checks the token on the next request.
      final saved = await _s.db.getCache('me');
      state = SessionState(user: saved == null ? null : SessionUser.fromJson(saved.body as Map<String, dynamic>));
    } on ApiException {
      await signOut();
    }
  }

  /// Accept a token from login or registration. Staff roles are refused: they use the web console.
  Future<void> signIn(Map<String, dynamic> tokenResponse) async {
    final user = SessionUser.fromJson(tokenResponse['user'] as Map<String, dynamic>);
    if (!appRoles.contains(user.role)) {
      throw ApiException(403, 'Officers use the ScholarSetu web console, not this app.');
    }
    final previous = await _s.db.getCache('me');
    if (previous != null && (previous.body as Map)['id'] != user.id) {
      await _s.db.wipe(); // a different person: nothing of the previous user's may remain
    }
    await _s.secure.setToken(tokenResponse['access_token'] as String);
    _s.api.token = tokenResponse['access_token'] as String;
    await _s.db.putCache('me', tokenResponse['user']);
    state = SessionState(user: user);
  }

  Future<void> signOut() async {
    _s.api.token = null;
    _s.api.mitraSessionId = null;
    await _s.secure.clearToken();
    await _s.db.wipe();
    state = const SessionState();
  }
}

final sessionProvider = NotifierProvider<SessionNotifier, SessionState>(SessionNotifier.new);

// ── connection (what actually happened on the last request, not a guess) ────

class ConnectionInfo {
  const ConnectionInfo({this.reachable, this.since});

  final bool? reachable; // null until the first request
  final DateTime? since;
}

class ConnectionNotifier extends Notifier<ConnectionInfo> {
  @override
  ConnectionInfo build() {
    ref.read(servicesProvider).api.onReachability = (ok) {
      if (state.reachable != ok) state = ConnectionInfo(reachable: ok, since: DateTime.now());
    };
    return const ConnectionInfo();
  }
}

final connectionProvider = NotifierProvider<ConnectionNotifier, ConnectionInfo>(ConnectionNotifier.new);

// ── outbox and sync ───────────────────────────────────────────────────────

class OutboxView {
  const OutboxView({this.items = const [], this.lastSync, this.lastReport});

  final List<OutboxRow> items;
  final DateTime? lastSync;
  final SyncReport? lastReport;

  int get pending => items.where((i) => i.status == 'PENDING').length;
  List<OutboxRow> get refused => items.where((i) => i.status == 'REJECTED').toList();
}

class OutboxNotifier extends Notifier<OutboxView> {
  Services get _s => ref.read(servicesProvider);

  @override
  OutboxView build() {
    Future.microtask(refresh);
    return const OutboxView();
  }

  Future<void> refresh([SyncReport? report]) async {
    state = OutboxView(items: await _s.db.outbox(), lastSync: await _s.repo.lastSync(),
        lastReport: report ?? state.lastReport);
  }

  Future<SyncReport> syncNow() async {
    final report = await _s.repo.sync();
    await refresh(report);
    return report;
  }

  Future<void> dismiss(String key) async {
    await _s.db.dismissOutbox(key);
    await refresh();
  }
}

final outboxProvider = NotifierProvider<OutboxNotifier, OutboxView>(OutboxNotifier.new);

// ── read models (cached) ──────────────────────────────────────────────────

FutureProvider<Cached<dynamic>> _cachedProvider(String key, String path) =>
    FutureProvider<Cached<dynamic>>((ref) => ref.read(servicesProvider).repo.cached(key, path));

final dashboardProvider = _cachedProvider('dashboard', '/me/dashboard');
final householdProvider = _cachedProvider('household', '/me/household');
final paymentsProvider = _cachedProvider('payments', '/me/payments');
final passportProvider = _cachedProvider('passport', '/me/attestations');
final pathwayProvider = _cachedProvider('pathway', '/me/pathway');
final pendingActionsProvider = _cachedProvider('pending', '/me/pending-actions');
final walletProvider = _cachedProvider('wallet', '/me/wallet');
final notificationsProvider = _cachedProvider('notifications', '/notifications');
