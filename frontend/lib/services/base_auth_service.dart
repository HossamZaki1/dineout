import 'package:firebase_auth/firebase_auth.dart';

abstract class BaseAuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;

  // Get current user
  User? get currentUser => _auth.currentUser;

  // Auth state changes stream
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  // Check if email is verified
  bool get isEmailVerified => _auth.currentUser?.emailVerified ?? false;

  // Reload user to get updated email verification status
  Future<void> reloadUser() async {
    await _auth.currentUser?.reload();
  }

  // Delete account
  Future<void> deleteAccount() async {
    try {
      await _auth.currentUser?.delete();
    } on FirebaseAuthException catch (e) {
      throw handleAuthException(e);
    }
  }

  // Handle Firebase Auth exceptions - made protected for child classes
  String handleAuthException(FirebaseAuthException e) {
    switch (e.code) {
      case 'user-not-found':
        return 'No user found for that email.';
      case 'wrong-password':
        return 'Wrong password provided for that user.';
      case 'email-already-in-use':
        return 'The account already exists for that email.';
      case 'weak-password':
        return 'The password provided is too weak.';
      case 'invalid-email':
        return 'The email address is not valid.';
      case 'user-disabled':
        return 'This user account has been disabled.';
      case 'too-many-requests':
        return 'Too many requests. Try again later.';
      case 'operation-not-allowed':
        return 'This operation is not allowed.';
      case 'invalid-verification-code':
        return 'The verification code is invalid.';
      case 'invalid-verification-id':
        return 'The verification ID is invalid.';
      case 'quota-exceeded':
        return 'SMS quota exceeded. Try again later.';
      case 'invalid-phone-number':
        return 'The phone number is invalid.';
      case 'missing-phone-number':
        return 'Phone number is required.';
      default:
        return e.message ?? 'An authentication error occurred.';
    }
  }

  // Protected getter for FirebaseAuth instance
  FirebaseAuth get auth => _auth;
}
