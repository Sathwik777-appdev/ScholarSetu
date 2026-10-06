/// Build-time configuration. Pass `--dart-define=API_URL=http://...` for custom environments.
/// The default reaches this development host machine on the current local network.
const String defaultApiOrigin = String.fromEnvironment('API_URL', defaultValue: 'https://scholarsetu-api.onrender.com');

String formatBaseUrl(String origin) {
  var clean = origin.trim().replaceAll(RegExp(r'/$'), '');
  if (!clean.endsWith('/v1')) {
    clean = '$clean/v1';
  }
  return clean;
}

String formatOrigin(String url) {
  var clean = url.trim().replaceAll(RegExp(r'/$'), '');
  if (clean.endsWith('/v1')) {
    clean = clean.substring(0, clean.length - 3);
  }
  return clean;
}

const String apiOrigin = defaultApiOrigin;
final String apiBaseUrl = formatBaseUrl(defaultApiOrigin);

/// How often the app checks for new events and notifications while it is open (there is no push: see
/// ARCHITECTURE.md §19, "Push notifications").
const Duration pollInterval = Duration(seconds: 60);

/// Demo builds (--dart-define=DEMO_ACCOUNTS=true) show one-tap seeded demo accounts. The server still
/// decides: it accepts the demo code only for seeded demo users and only in DEMO_MODE.
const bool demoAccounts = bool.fromEnvironment('DEMO_ACCOUNTS');
const String demoOtp = String.fromEnvironment('DEMO_OTP', defaultValue: '123456');
