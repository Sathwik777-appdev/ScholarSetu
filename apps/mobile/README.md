# ScholarSetu mobile app (Flutter)

The app for students, parents/guardians (family mode) and Mitra helpers. Officers and the ministry use
the web console in `apps/console`.

## What it does

- **Sign in / register** with a phone number confirmed by an SMS code. Registering creates the account
  only; the home screen then says **"Registered — application NOT submitted"** until an application is sent.
- **Offline first.** Read screens show the last copy saved on the phone with **"Saved copy. Last updated …"**
  when the server cannot be reached, or an error if nothing was saved. Nothing is invented.
- **Outbox.** Applications, replies to office queries, document uploads and "mark as read" are saved in a
  persistent outbox with an idempotency key, and sent in order when the connection returns
  (`POST /v1/sync/outbox`, uploads with `Idempotency-Key`). The server applies each key once. Refused items
  stay visible under **Sync** with the server's reason.
- **Delta sync.** Ledger events for your applications arrive through `GET /v1/sync?cursor=…`.
- **Encrypted local store.** Drift over SQLCipher (selected in `pubspec.yaml` through `package:sqlite3`'s
  build hook). The 256-bit key is created on first run and kept in `flutter_secure_storage`. The app checks
  `PRAGMA cipher_version` at start and refuses to run if the library is not SQLCipher.
- **Notifications** are polled every minute while the app is open (no FCM; see ARCHITECTURE.md §19).
- **Mitra mode** follows the server flow: the helper starts a session, the student receives the code by SMS
  and reads it out (the field is never pre-filled), and the session ends or expires. Nothing about the
  student is cached on the helper's phone.

## Run

```bash
flutter pub get
flutter analyze
flutter test
# Android emulator talking to the API on your machine (default):
flutter run
# Any other API:
flutter run --dart-define=API_URL=https://api.example.org
flutter build apk --debug
```

Plain HTTP is allowed only to `10.0.2.2` and `localhost` (`android/app/src/main/res/xml/network_security_config.xml`).
