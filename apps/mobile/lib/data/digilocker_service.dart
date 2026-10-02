import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

import 'api.dart';

/// What "Sign in with DigiLocker" ended in.
sealed class DigiLockerResult {}

/// A known person: the server's token response (access_token + user), ready for SessionNotifier.signIn.
class DigiLockerSignedIn extends DigiLockerResult {
  DigiLockerSignedIn(this.auth);
  final Map<String, dynamic> auth;
}

/// A new person: DigiLocker confirmed who they are; they finish a short sign-up with this token.
class DigiLockerNeedsSignup extends DigiLockerResult {
  DigiLockerNeedsSignup(this.registrationToken, this.profile);
  final String registrationToken;
  final Map<String, dynamic> profile; // name, dob, gender as DigiLocker gave them
}

/// The person closed DigiLocker without finishing.
class DigiLockerCancelled extends DigiLockerResult {}

/// Sign in with DigiLocker (OAuth 2.0 + PKCE). The server creates the state and PKCE verifier and does the token
/// exchange with the client secret; the app only opens DigiLocker and hands back the code.
class DigiLockerSignIn {
  DigiLockerSignIn(this.api);
  final Api api;

  Future<DigiLockerResult> run() async {
    final start = await api.post('/auth/digilocker/start') as Map<String, dynamic>;
    final redirect = Uri.parse(start['redirect_uri'] as String);
    String result;
    try {
      result = await FlutterWebAuth2.authenticate(url: start['authorize_url'] as String, callbackUrlScheme: redirect.scheme);
    } catch (_) {
      return DigiLockerCancelled(); // closed the browser or pressed back
    }
    final params = Uri.parse(result).queryParameters;
    if (params['code'] == null || params['state'] != start['state']) {
      throw ApiException(400, params['error_description'] ?? params['error'] ?? 'DigiLocker did not finish the sign-in.');
    }
    final done = await api.post('/auth/digilocker/complete', {'state': params['state'], 'code': params['code']})
        as Map<String, dynamic>;
    if (done['status'] == 'SIGNED_IN') return DigiLockerSignedIn(done['auth'] as Map<String, dynamic>);
    return DigiLockerNeedsSignup(done['registration_token'] as String, (done['profile'] as Map).cast<String, dynamic>());
  }
}
