import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secrets that must never sit in the (encrypted) database file itself: the database key and the
/// access and refresh tokens. Held in the Android Keystore / iOS Keychain via flutter_secure_storage.
class SecureStore {
  SecureStore([FlutterSecureStorage? storage]) : _s = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _s;
  static const _dbKey = 'db_key_v1';
  static const _token = 'access_token';
  static const _refresh = 'refresh_token';
  static const _apiUrlKey = 'custom_api_url';
  static const _langKey = 'language';
  static const _demoKey = 'demo_mode';

  /// A random 256-bit key, created on first use and kept for the life of the install.
  Future<String> databaseKey() async {
    final existing = await _s.read(key: _dbKey);
    if (existing != null && existing.length == 64) return existing;
    final rnd = Random.secure();
    final key = List.generate(32, (_) => rnd.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
    await _s.write(key: _dbKey, value: key);
    return key;
  }

  Future<String?> token() => _s.read(key: _token);
  Future<String?> refreshToken() => _s.read(key: _refresh);

  /// Both tokens together: the refresh token is single-use, so a renewed pair must be saved before it is relied on.
  Future<void> setTokens(String access, String? refresh) async {
    await _s.write(key: _token, value: access);
    if (refresh != null) await _s.write(key: _refresh, value: refresh);
  }

  Future<void> clearToken() async {
    await _s.delete(key: _token);
    await _s.delete(key: _refresh);
  }

  Future<String?> apiUrl() => _s.read(key: _apiUrlKey);
  Future<void> setApiUrl(String value) => _s.write(key: _apiUrlKey, value: value);
  Future<void> clearApiUrl() => _s.delete(key: _apiUrlKey);

  // Preferences that must survive sign-out (the database is wiped then).
  Future<String?> language() => _s.read(key: _langKey);
  Future<void> setLanguage(String value) => _s.write(key: _langKey, value: value);
  Future<bool> demoMode() async => (await _s.read(key: _demoKey)) == 'on';
  Future<void> setDemoMode(bool on) => _s.write(key: _demoKey, value: on ? 'on' : 'off');
}
