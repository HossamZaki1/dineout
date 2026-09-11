import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/google_auth_service.dart';
import 'package:google_sign_in_platform_interface/google_sign_in_platform_interface.dart';

class FakeGooglePlatform extends GoogleSignInPlatform {
  int initializations = 0;
  final ready = Completer<void>();
  @override
  Future<void> init(InitParameters params) {
    initializations++;
    return ready.future;
  }

  @override
  Stream<AuthenticationEvent>? get authenticationEvents => null;

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnsupportedError(
    'Unexpected Google platform call: ${invocation.memberName}',
  );
}

void main() {
  test(
    'native Google initialization is awaited and shared by concurrent callers',
    () async {
      final platform = FakeGooglePlatform();
      GoogleSignInPlatform.instance = platform;
      var finished = false;
      final first = GoogleAuthService.initialize().then((_) => finished = true);
      final second = GoogleAuthService.initialize();
      expect(platform.initializations, 1);
      await Future<void>.delayed(Duration.zero);
      expect(finished, isFalse);
      platform.ready.complete();
      await Future.wait([first, second]);
      expect(finished, isTrue);
      expect(platform.initializations, 1);
    },
  );
}
