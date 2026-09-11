import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/config/api_config.dart';

/// These run on the host VM, so `Platform.isAndroid` is false and `kIsWeb` is
/// false, which is exactly the case that used to break: a checked-in `.env`
/// holding the Android emulator alias.
void main() {
  setUp(() => dotenv.clean());

  group('ApiConfig.baseUrl', () {
    test('uses the configured URL', () {
      dotenv.testLoad(fileInput: 'API_URL=https://api.example.com');
      expect(ApiConfig.baseUrl, 'https://api.example.com');
    });

    test('rewrites the Android emulator alias when not on Android', () {
      dotenv.testLoad(fileInput: 'API_URL=http://10.0.2.2:8080');
      expect(ApiConfig.baseUrl, 'http://localhost:8080');
    });

    test('falls back to API_BASE_URL', () {
      dotenv.testLoad(fileInput: 'API_BASE_URL=https://other.example.com');
      expect(ApiConfig.baseUrl, 'https://other.example.com');
    });

    test('does not throw in debug when nothing is configured', () {
      dotenv.testLoad(fileInput: '');
      expect(() => ApiConfig.baseUrl, returnsNormally);
    });

    test('does not throw when dotenv never loaded', () {
      // main() swallows a failed load, and a throw here would poison the
      // lazily-initialised HTTP client for the whole process.
      expect(() => ApiConfig.baseUrl, returnsNormally);
    });
  });

  group('ApiConfig.resolveMedia', () {
    setUp(() => dotenv.testLoad(fileInput: 'API_URL=https://api.example.com'));

    test('prefixes a relative photo path with the API base', () {
      expect(
        ApiConfig.resolveMedia('/photos/place123/photo456'),
        'https://api.example.com/photos/place123/photo456',
      );
    });

    test('passes absolute URLs through unchanged', () {
      // Conversations saved before the photo route existed hold absolute URLs.
      const legacy = 'https://places.googleapis.com/v1/places/x/photos/y/media';
      expect(ApiConfig.resolveMedia(legacy), legacy);
    });

    test('does not double up slashes', () {
      dotenv.clean();
      dotenv.testLoad(fileInput: 'API_URL=https://api.example.com/');
      expect(
        ApiConfig.resolveMedia('/photos/a/b'),
        'https://api.example.com/photos/a/b',
      );
    });

    test('handles a path with no leading slash', () {
      expect(
        ApiConfig.resolveMedia('photos/a/b'),
        'https://api.example.com/photos/a/b',
      );
    });
  });
}
