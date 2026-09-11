import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/photo_service.dart';

class PhotoAdapter implements HttpClientAdapter {
  final requests = <RequestOptions>[];
  int status = 200;
  String url = 'https://images.example/restaurant.jpg';
  Completer<void>? pending;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    if (pending != null) await pending!.future;
    return ResponseBody.fromString(
      jsonEncode({'url': url}),
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  late PhotoAdapter adapter;
  late PhotoService photos;
  String? uid;

  setUp(() {
    uid = 'alice';
    adapter = PhotoAdapter();
    final client = Dio(
      BaseOptions(
        baseUrl: 'https://api.example',
        headers: {'Authorization': 'Bearer test-token'},
      ),
    )..httpClientAdapter = adapter;
    photos = PhotoService(client: client, userId: () => uid);
  });

  test(
    'concurrent photo loads resolve once through the authenticated API',
    () async {
      final urls = await Future.wait([
        photos.resolve('/photos/place/photo'),
        photos.resolve('/photos/place/photo'),
      ]);
      expect(urls, everyElement('https://images.example/restaurant.jpg'));
      expect(adapter.requests, hasLength(1));
      expect(adapter.requests.single.uri.host, 'api.example');
      expect(adapter.requests.single.queryParameters['redirect'], false);
      expect(
        adapter.requests.single.headers['Authorization'],
        'Bearer test-token',
      );
    },
  );

  test(
    'legacy Maps keys are stripped and external images receive no API call',
    () async {
      await photos.resolve(
        'https://places.googleapis.com/v1/places/place/photos/photo/media?key=old-secret',
      );
      expect(
        adapter.requests.single.uri.toString(),
        isNot(contains('old-secret')),
      );
      expect(adapter.requests.single.path, '/photos/place/photo');
      expect(
        await photos.resolve('https://images.example/public.jpg'),
        'https://images.example/public.jpg',
      );
      expect(adapter.requests, hasLength(1));
    },
  );

  test('photo cache is isolated by account and requires sign-in', () async {
    await photos.resolve('/photos/place/photo');
    uid = 'bob';
    await photos.resolve('/photos/place/photo');
    expect(adapter.requests, hasLength(2));
    uid = null;
    await expectLater(photos.resolve('/photos/place/photo'), throwsStateError);
  });

  test('failed photo resolution can be retried', () async {
    adapter.status = 503;
    await expectLater(
      photos.resolve('/photos/place/photo'),
      throwsA(isA<DioException>()),
    );
    adapter.status = 200;
    expect(await photos.resolve('/photos/place/photo'), startsWith('https://'));
    expect(adapter.requests, hasLength(2));
  });

  test('late responses from a previous account are discarded', () async {
    adapter.pending = Completer<void>();
    final pending = photos.resolve('/photos/place/photo');
    final failure = expectLater(pending, throwsStateError);
    uid = 'bob';
    adapter.pending!.complete();
    await failure;
  });

  test(
    'invalid references and insecure upstream image URLs are rejected',
    () async {
      await expectLater(
        photos.resolve('/photos/place/../photo'),
        throwsStateError,
      );
      expect(adapter.requests, isEmpty);
      adapter.url = 'http://images.example/photo';
      await expectLater(
        photos.resolve('/photos/place/photo'),
        throwsStateError,
      );
    },
  );
}
