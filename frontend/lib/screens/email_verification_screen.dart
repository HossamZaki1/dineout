import 'package:flutter/material.dart';
import 'dart:async';
import '../services/auth_service.dart';

class EmailVerificationScreen extends StatefulWidget {
  const EmailVerificationScreen({super.key});

  @override
  State<EmailVerificationScreen> createState() => _EmailVerificationScreenState();
}

class _EmailVerificationScreenState extends State<EmailVerificationScreen> {
  final AuthService _authService = AuthService();
  bool _isLoading = false;
  bool _canResendEmail = false;
  Timer? _timer;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _checkEmailVerification();
    _startEmailVerificationTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startEmailVerificationTimer() {
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => _checkEmailVerification());

    // Allow resending email after 30 seconds
    Timer(const Duration(seconds: 30), () {
      if (mounted) {
        setState(() {
          _canResendEmail = true;
        });
      }
    });
  }

  Future<void> _checkEmailVerification() async {
    await _authService.reloadUser();

    if (_authService.isEmailVerified) {
      _timer?.cancel();
      if (mounted) {
        Navigator.pushReplacementNamed(context, '/home');
      }
    }
  }

  Future<void> _resendVerificationEmail() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _canResendEmail = false;
    });

    try {
      await _authService.sendEmailVerification();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Verification email sent! Please check your inbox.'),
            backgroundColor: Colors.green,
          ),
        );

        // Reset the timer for resending
        Timer(const Duration(seconds: 30), () {
          if (mounted) {
            setState(() {
              _canResendEmail = true;
            });
          }
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _canResendEmail = true;
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _signOut() async {
    await _authService.signOut();
    if (mounted) {
      Navigator.pushReplacementNamed(context, '/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Email Icon
              Center(
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        color: Theme.of(context).primaryColor.withOpacity(0.1),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.email_outlined,
                        size: 80,
                        color: Theme.of(context).primaryColor,
                      ),
                    ),

                    const SizedBox(height: 24),

                    const Text(
                      'Verify Your Email',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),

                    const SizedBox(height: 16),

                    Text(
                      'We sent a verification link to\n${_authService.currentUser?.email ?? "your email"}',
                      style: const TextStyle(
                        fontSize: 16,
                        color: Colors.grey,
                      ),
                      textAlign: TextAlign.center,
                    ),

                    const SizedBox(height: 8),

                    const Text(
                      'Please check your inbox and click the verification link to continue.',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 40),

              // Error message
              if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade700),
                  ),
                ),

              // Loading indicator
              const Center(
                child: Column(
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text(
                      'Checking verification status...',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 40),

              // Resend Email Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton(
                  onPressed: _canResendEmail && !_isLoading ? _resendVerificationEmail : null,
                  child: _isLoading
                      ? const CircularProgressIndicator()
                      : Text(
                          _canResendEmail
                              ? 'Resend Verification Email'
                              : 'Resend Available in 30s',
                          style: const TextStyle(fontSize: 16),
                        ),
                ),
              ),

              const SizedBox(height: 16),

              // Manual Check Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _checkEmailVerification,
                  child: const Text(
                    'I\'ve Verified My Email',
                    style: TextStyle(fontSize: 16),
                  ),
                ),
              ),

              const SizedBox(height: 32),

              // Help Section
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Having trouble?',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.blue.shade700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '• Check your spam/junk folder\n'
                      '• Make sure the email address is correct\n'
                      '• Wait a few minutes for the email to arrive\n'
                      '• Try resending the verification email',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.blue.shade600,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Sign Out Button
              TextButton(
                onPressed: _signOut,
                child: const Text(
                  'Sign Out',
                  style: TextStyle(color: Colors.red),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
