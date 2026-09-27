/// Build-time configuration. Pass `--dart-define=API_URL=https://...` for other environments.
/// The default reaches the host machine from the Android emulator.
const String apiOrigin = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000');
final String apiBaseUrl = '${apiOrigin.replaceAll(RegExp(r'/$'), '')}/v1';

/// How often the app checks for new events and notifications while it is open (there is no push: see
/// ARCHITECTURE.md §19, "Push notifications").
const Duration pollInterval = Duration(seconds: 60);
