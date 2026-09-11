import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'api_client.dart';

class PhotoService {
  static final instance = PhotoService();
  final Dio? client;
  final String? Function()? userId;
  final _cache = <String, ({DateTime expires, Future<String> url})>{};

  PhotoService({this.client, this.userId});

  String? get _currentUserId =>
      userId != null ? userId!() : FirebaseAuth.instance.currentUser?.uid;

  Future<String> resolve(String reference) {
    final uid = _currentUserId;
    if (uid == null) return Future.error(StateError('Sign in to view photos'));
    var path = reference;
    final uri = Uri.tryParse(reference);
    if (uri != null && uri.hasScheme) {
      // Upgrade old stored Maps URLs without forwarding their obsolete keys.
      final match = RegExp(
        r'^/v1/places/([^/]+)/photos/([^/]+)/media$',
      ).firstMatch(uri.path);
      if (uri.host == 'places.googleapis.com' && match != null) {
        path = '/photos/${match[1]}/${match[2]}';
      } else if (uri.scheme == 'https') {
        return Future.value(
          reference,
        ); // Never send a token to an external host.
      } else {
        return Future.error(StateError('Invalid photo URL'));
      }
    }
    if (!RegExp(r'^/photos/[A-Za-z0-9_=-]+/[A-Za-z0-9_=-]+$').hasMatch(path)) {
      return Future.error(StateError('Invalid photo reference'));
    }
    final key = '$uid:$path';
    final cached = _cache[key];
    if (cached != null && cached.expires.isAfter(DateTime.now())) {
      return cached.url;
    }
    final future = _resolve(path, uid);
    _cache.remove(key);
    _cache[key] = (
      expires: DateTime.now().add(const Duration(minutes: 4)),
      url: future,
    );
    while (_cache.length > 128) {
      _cache.remove(_cache.keys.first);
    }
    // Observe failures without leaving a rejected future permanently cached.
    future.then<void>(
      (_) {},
      onError: (Object error, StackTrace stack) {
        if (identical(_cache[key]?.url, future)) _cache.remove(key);
      },
    );
    return future;
  }

  Future<String> _resolve(String path, String uid) async {
    final response = await (client ?? ApiClient.instance).get(
      path,
      queryParameters: {'redirect': false},
    );
    if (_currentUserId != uid) throw StateError('Sign in to view photos');
    final url = response.data['url'] as String;
    final uri = Uri.tryParse(url);
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
      throw StateError('Invalid photo URL');
    }
    return url;
  }
}
