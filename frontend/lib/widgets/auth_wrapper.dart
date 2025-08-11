import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../services/auth_service.dart';
import '../screens/login_screen.dart';
import '../screens/email_verification_screen.dart';
import '../main.dart'; // Your main app screen

class AuthWrapper extends StatelessWidget {
  const AuthWrapper({super.key});

  @override
  Widget build(BuildContext context) {
    final AuthService authService = AuthService();

    return StreamBuilder<User?>(
      stream: authService.authStateChanges,
      builder: (context, snapshot) {
        // Show loading screen while checking auth state
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: Center(
              child: CircularProgressIndicator(),
            ),
          );
        }

        // User is signed in
        if (snapshot.hasData) {
          final user = snapshot.data!;

          // Check if email is verified (for email/password users)
          if (user.providerData.any((info) => info.providerId == 'password') &&
              !user.emailVerified) {
            return const EmailVerificationScreen();
          }

          // User is signed in and verified, show main app
          return const MyHomePage(title: 'DineOut AI');
        }

        // User is not signed in, show login screen
        return const LoginScreen();
      },
    );
  }
}
