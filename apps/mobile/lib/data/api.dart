import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../i18n.dart';

/// The server answered with an error. `detail` is the API's own explanation.
class ApiException implements Exception {
  ApiException(this.status, this.detail, [this.code]);

  final int status;
  final dynamic detail;
  final String? code; // e.g. WAKING: the server is starting up after being idle

  /// 4xx other than timeouts/rate limits: resending the same request will not help.
  bool get isPermanent => status >= 400 && status < 500 && status != 408 && status != 429;

  String get message {
    final d = detail;
    if (d is String) return d;
    if (d is Map && d['message'] is String) return d['message'] as String;
    if (status == 401) return t('Please sign in again.', 'कृपया फिर से साइन इन करें।');
    if (status == 403) return t('You are not allowed to do this.', 'आपको यह करने की अनुमति नहीं है।');
    return t('The server returned an error ($status).', 'सर्वर से त्रुटि आई ($status)।');
  }

  @override
  String toString() => message;
}

/// The server could not be reached (no network, DNS failure, timeout).
class OfflineException implements Exception {
  OfflineException([this.serverUrl]);
  final String? serverUrl;

  @override
  String toString() => serverUrl != null
      ? t('No connection to ScholarSetu ($serverUrl).', 'ScholarSetu से कनेक्शन नहीं है ($serverUrl)।')
      : t('No connection to ScholarSetu.', 'ScholarSetu से कनेक्शन नहीं है।');
}

typedef ReachabilityListener = void Function(bool reachable);

class Api {
  Api(this.baseUrl, {http.Client? client}) : _client = client ?? http.Client();

  String baseUrl;
  final http.Client _client;
  String? token;
  String? mitraSessionId;
  ReachabilityListener? onReachability;
  void Function()? onUnauthorized;

  static const _timeout = Duration(seconds: 30);

  Map<String, String> _headers([Map<String, String>? extra]) => {
        'Accept': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
        if (mitraSessionId != null) 'X-Mitra-Session': mitraSessionId!,
        ...?extra,
      };

  Future<dynamic> get(String path, {Map<String, String>? query}) =>
      _send(() => _client.get(Uri.parse('$baseUrl$path').replace(queryParameters: query), headers: _headers()));

  Future<dynamic> post(String path, [Object? body]) => _send(() => _client.post(Uri.parse('$baseUrl$path'),
      headers: _headers({'Content-Type': 'application/json'}), body: jsonEncode(body ?? {})));

  Future<dynamic> delete(String path) => _send(() => _client.delete(Uri.parse('$baseUrl$path'), headers: _headers()));

  Future<dynamic> upload(String path, Map<String, String> fields, Uint8List bytes, String fileName,
      {String? idempotencyKey}) {
    return _send(() async {
      final request = http.MultipartRequest('POST', Uri.parse('$baseUrl$path'))
        ..headers.addAll(_headers({if (idempotencyKey != null) 'Idempotency-Key': idempotencyKey}))
        ..fields.addAll(fields)
        ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: fileName));
      return http.Response.fromStream(await _client.send(request));
    });
  }

  Future<dynamic> _send(Future<http.Response> Function() call) async {
    http.Response res;
    try {
      res = await call().timeout(_timeout);
    } on SocketException {
      onReachability?.call(false);
      throw OfflineException(baseUrl);
    } on TimeoutException {
      onReachability?.call(false);
      throw OfflineException(baseUrl);
    } on http.ClientException {
      onReachability?.call(false);
      throw OfflineException(baseUrl);
    } on HandshakeException {
      onReachability?.call(false);
      throw OfflineException(baseUrl);
    } on IOException {
      onReachability?.call(false);
      throw OfflineException(baseUrl);
    }
    onReachability?.call(true);
    final text = utf8.decode(res.bodyBytes);
    dynamic body;
    try {
      body = text.isEmpty ? null : jsonDecode(text);
    } on FormatException {
      body = text;
    }
    if (res.statusCode >= 200 && res.statusCode < 300) return body;
    if (res.statusCode == 401 && token != null) onUnauthorized?.call();
    throw ApiException(res.statusCode, body is Map ? body['detail'] : body, body is Map ? body['code'] as String? : null);
  }
}
