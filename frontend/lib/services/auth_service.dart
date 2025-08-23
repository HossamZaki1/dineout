import 'package:firebase_auth/firebase_auth.dart';
import 'email_auth_service.dart';
import 'google_auth_service.dart';
import 'phone_auth_service.dart';
import 'base_auth_service.dart';

class AuthService extends BaseAuthService {
  final EmailAuthService _emailAuth = EmailAuthService();
  final GoogleAuthService _googleAuth = GoogleAuthService();
  final PhoneAuthService _phoneAuth = PhoneAuthService();

  // Email/Password Authentication Methods
  Future<UserCredential?> signUpWithEmailPassword(String email, String password) async {
    return await _emailAuth.signUpWithEmailPassword(email, password);
  }

  Future<UserCredential?> signInWithEmailPassword(String email, String password) async {
    return await _emailAuth.signInWithEmailPassword(email, password);
  }

  Future<void> sendEmailVerification() async {
    await _emailAuth.sendEmailVerification();
  }

  Future<void> sendPasswordResetEmail(String email) async {
    await _emailAuth.sendPasswordResetEmail(email);
  }

  // Google Authentication Methods
  Future<UserCredential?> signInWithGoogle() async {
    return await _googleAuth.signInWithGoogle();
  }

  // Phone Authentication Methods
  Future<void> verifyPhoneNumber({
    required String phoneNumber,
    required Function(PhoneAuthCredential) verificationCompleted,
    required Function(FirebaseAuthException) verificationFailed,
    required Function(String, int?) codeSent,
    required Function(String) codeAutoRetrievalTimeout,
  }) async {
    await _phoneAuth.verifyPhoneNumber(
      phoneNumber: phoneNumber,
      verificationCompleted: verificationCompleted,
      verificationFailed: verificationFailed,
      codeSent: codeSent,
      codeAutoRetrievalTimeout: codeAutoRetrievalTimeout,
    );
  }

  Future<UserCredential?> signInWithPhoneCredential(String verificationId, String smsCode) async {
    return await _phoneAuth.signInWithPhoneCredential(verificationId, smsCode);
  }

  // Universal Sign Out - handles all auth methods
  Future<void> signOut() async {
    await _googleAuth.signOut(); // This also handles Firebase signOut
  }
}
