import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsetu_mobile/ui/student_screens.dart';

void main() {
  test('a test DigiLocker document is labelled as test data, never issuer-signed', () {
    expect(documentSourceText({'source': 'DIGILOCKER_TEST', 'source_label': 'DigiLocker (test)',
        'test_document': true, 'verified': false}), 'From DigiLocker (test) · test data, not verified');
  });

  test('only a verified document says issuer-signed', () {
    expect(documentSourceText({'source': 'DIGILOCKER', 'source_label': 'DigiLocker', 'verified': true}),
        'From DigiLocker · issuer-signed');
    expect(documentSourceText({'source': 'UPLOAD', 'source_label': 'Uploaded by you', 'verified': false}),
        'Uploaded by you · not verified');
  });
}
