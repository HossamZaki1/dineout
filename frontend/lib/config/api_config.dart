import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kDebugMode, kIsWeb;
import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Resolves the base URL of the DineQuest backend.
///
/// A configured `API_URL` always wins, on every platform. The platform
/// fallbacks below exist only so a debug build can reach a backend running on
/// the development machine; a release build with no `API_URL` is a packaging
/// mistake and fails loudly rather than pointing at localhost.
class ApiConfig {
  static String get baseUrl {
    // dotenv throws if load() failed, and main() swallows that failure. A
    // throwing lazy static would poison ApiClient for the whole process.
    final configured = dotenv.isInitialized
        ? (dotenv.env['API_URL'] ?? dotenv.env['API_BASE_URL'])
        : null;

    if (configured != null && configured.isNotEmpty) {
      // 10.0.2.2 is defined only as the Android emulator's alias for the host
      // machine, and is unroutable anywhere else. Correct it rather than
      // letting a checked-in development value break web and iOS.
      if (configured.contains('10.0.2.2') && (kIsWeb || !Platform.isAndroid)) {
        return configured.replaceFirst('10.0.2.2', 'localhost');
      }
      return configured;
    }

    if (!kDebugMode) {
      throw StateError(
        'API_URL is not configured. Set it in the .env file bundled with the '
        'app before building for release.',
      );
    }

    // Debug only: the Android emulator reaches the host machine on 10.0.2.2,
    // everything else can use localhost directly.
    if (kIsWeb) return 'http://localhost:8080';
    if (Platform.isAndroid) return 'http://10.0.2.2:8080';
    return 'http://localhost:8080';
  }

  /// Resolve a media reference returned by the backend into a loadable URL.
  ///
  /// The backend returns paths like `/photos/<place>/<photo>` and serves the
  /// image itself, so the Maps API key stays on the server. Conversations
  /// saved before that change hold absolute URLs, which are passed through
  /// unchanged even though their key is now dead.
  static String resolveMedia(String pathOrUrl) {
    if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
      return pathOrUrl;
    }
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    return pathOrUrl.startsWith('/') ? '$base$pathOrUrl' : '$base/$pathOrUrl';
  }
}
