import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'base_auth_service.dart';

class GoogleAuthService extends BaseAuthService {
  GoogleAuthService(); // <- not const

  /// Returns null if the user cancels.
  Future<UserCredential?> signInWithGoogle() async {
    try {
      if (kIsWeb) {
        // Use Firebase's web popup flow directly.
        final provider = GoogleAuthProvider()
          ..setCustomParameters({'prompt': 'select_account'});
        return await auth.signInWithPopup(provider);
      }

      // v7 flow: start authentication
      final account = await GoogleSignIn.instance.authenticate();

      // v7: only idToken is provided here
      final idToken = account.authentication.idToken;
      if (idToken == null) {
        throw FirebaseAuthException(
          code: 'missing-id-token',
          message:
          'No idToken from Google. On Android ensure google-services.json has a Web OAuth client or pass serverClientId to GoogleSignIn.initialize; on iOS/macOS set clientId.',
        );
      }

      final credential = GoogleAuthProvider.credential(idToken: idToken);
      return await auth.signInWithCredential(credential);
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled) return null;
      throw Exception('Google sign-in failed (${e.code}): ${e.description ?? 'unknown error'}');
    } on FirebaseAuthException catch (e) {
      throw handleAuthException(e);
    }
  }

  Future<void> signOut() async {
    await auth.signOut();
    if (!kIsWeb) {
      await GoogleSignIn.instance.signOut();
    }
  }
}
