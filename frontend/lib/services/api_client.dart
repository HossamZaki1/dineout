import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../config/api_config.dart';

/// Shared HTTP client for the DineQuest backend.
///
/// Attaches the signed-in user's Firebase ID token to every request. The
/// backend derives the caller's identity from that token, so no call needs to
/// pass a user ID, and no caller can claim to be someone else.
class ApiClient {
  static final Dio instance = _build();

  static Dio _build() {
    final dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: const Duration(seconds: 10),
        // Allow time for the search and its durable storage commit.
        receiveTimeout: const Duration(seconds: 120),
        sendTimeout: const Duration(seconds: 15),
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final user = FirebaseAuth.instance.currentUser;
          final requestUser = options.extra['authenticatedUid'];
          if (requestUser != null && requestUser != user?.uid) {
            return handler.reject(
              DioException(
                requestOptions: options,
                type: DioExceptionType.cancel,
                message: 'Authentication changed',
              ),
            );
          }
          options.headers.remove('Authorization');
          if (user != null) {
            options.extra['authenticatedUid'] = user.uid;
            try {
              final token = await user.getIdToken();
              if (user.uid != FirebaseAuth.instance.currentUser?.uid) {
                return handler.reject(
                  DioException(
                    requestOptions: options,
                    type: DioExceptionType.cancel,
                    message: 'Authentication changed',
                  ),
                );
              }
              if (token != null) {
                options.headers['Authorization'] = 'Bearer $token';
              }
            } catch (_) {
              // Send it unauthenticated and let the backend answer 401,
              // rather than failing here with a less useful error.
            }
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          // Firebase caches ID tokens for an hour. A 401 usually means the
          // cached one just aged out, so force a refresh and retry once.
          final isAuthFailure = error.response?.statusCode == 401;
          final alreadyRetried = error.requestOptions.extra['retried'] == true;
          final user = FirebaseAuth.instance.currentUser;

          if (isAuthFailure &&
              !alreadyRetried &&
              user != null &&
              error.requestOptions.extra['authenticatedUid'] == user.uid) {
            try {
              final token = await user.getIdToken(true);
              final options = error.requestOptions;
              options.extra['retried'] = true;
              options.headers['Authorization'] = 'Bearer $token';
              return handler.resolve(await instance.fetch(options));
            } catch (_) {
              // Refresh failed, so report the original error.
            }
          }
          handler.next(error);
        },
      ),
    );

    return dio;
  }
}
