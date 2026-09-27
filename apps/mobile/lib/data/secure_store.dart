import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secrets that must never sit in the (encrypted) database file itself: the database key and the
/// access token. Held in the Android Keystore / iOS Keychain via flutter_secure_storage.
class SecureStore {
  SecureStore([FlutterSecureStorage? storage]) : _s = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _s;
  static const _dbKey = 'db_key_v1';
  static const _token = 'access_token';

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
  Future<void> setToken(String value) => _s.write(key: _token, value: value);
  Future<void> clearToken() => _s.delete(key: _token);
}
