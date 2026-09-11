import 'package:firebase_auth/firebase_auth.dart';
import 'base_auth_service.dart';

class PhoneAuthService extends BaseAuthService {

  // Phone authentication - send verification code
  Future<void> verifyPhoneNumber({
    required String phoneNumber,
    required Function(PhoneAuthCredential) verificationCompleted,
    required Function(FirebaseAuthException) verificationFailed,
    required Function(String, int?) codeSent,
    required Function(String) codeAutoRetrievalTimeout,
  }) async {
    await auth.verifyPhoneNumber(
      phoneNumber: phoneNumber,
      verificationCompleted: verificationCompleted,
      verificationFailed: verificationFailed,
      codeSent: codeSent,
      codeAutoRetrievalTimeout: codeAutoRetrievalTimeout,
    );
  }

  // Verify phone number with SMS code
  Future<UserCredential?> signInWithPhoneCredential(String verificationId, String smsCode) async {
    try {
      PhoneAuthCredential credential = PhoneAuthProvider.credential(
        verificationId: verificationId,
        smsCode: smsCode,
      );

      UserCredential result = await auth.signInWithCredential(credential);
      return result;
    } on FirebaseAuthException catch (e) {
      throw handleAuthException(e);
    }
  }

  // Sign out (phone only)
  Future<void> signOut() async {
    await auth.signOut();
  }
}
