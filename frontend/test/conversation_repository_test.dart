import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/chat.dart';
import 'package:frontend/models/conversation.dart';
import 'package:frontend/services/conversation_repository.dart';
import 'package:frontend/services/conversation_service.dart';
import 'package:frontend/services/conversations_api_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class FakeApi extends ConversationsApiService {
  Object? failure;
  @override
  Future<ChatReply> chat(
    String sessionId,
    String text,
    List<Map<String, String>> history, {
    CancelToken? cancelToken,
  }) async {
    if (failure != null) throw failure!;
    return const ChatReply(
      text: 'Result',
      suggestions: [
        {'name': 'Restaurant', 'photo_url': '/photos/a/b'},
      ],
    );
  }

  @override
  Future<Map<String, dynamic>> getConversationFull(
    String sessionId, {
    CancelToken? cancelToken,
  }) async {
    throw failure!;
  }
}

void main() {
  late ConversationService local;
  late FakeApi api;
  late ConversationRepository repository;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    local = ConversationService();
    api = FakeApi();
    repository = ConversationRepository(
      userId: 'alice',
      currentUserId: () => 'alice',
      api: api,
      local: local,
    );
  });

  Future<void> seed() async {
    await local.upsertConversation(
      ConversationMeta(
        id: 'conversation',
        title: 'Custom title',
        createdAt: DateTime.utc(2026),
        updatedAt: DateTime.utc(2026),
        lastMessagePreview: 'Saved',
      ),
      userId: 'alice',
    );
    await local.saveConversationHistory('conversation', [
      ConversationMessage(
        role: 'user',
        content: 'Old message',
        timestamp: DateTime.utc(2026),
      ),
    ], userId: 'alice');
  }

  test(
    'successful replies preserve titles and cache suggestion metadata',
    () async {
      await seed();
      await repository.send('conversation', 'Pizza', []);
      final meta = await local.getConversationMeta(
        'conversation',
        userId: 'alice',
      );
      expect(meta!.title, 'Custom title');
      expect(meta.restaurantSuggestionNames, ['Restaurant']);
      expect(meta.totalRestaurantSuggestions, 1);
      expect(
        (await local.getConversationHistory(
          'conversation',
          userId: 'alice',
        ))!.length,
        3,
      );
    },
  );

  test('failed sends do not write successful-looking local history', () async {
    api.failure = StateError('network failed');
    await expectLater(
      repository.send('conversation', 'Pizza', []),
      throwsStateError,
    );
    expect(
      await local.getConversationHistory('conversation', userId: 'alice'),
      isNull,
    );
  });

  test(
    'a remote deletion purges cached messages instead of resurrecting them',
    () async {
      await seed();
      api.failure = DioException(
        requestOptions: RequestOptions(path: '/full'),
        response: Response(
          requestOptions: RequestOptions(path: '/full'),
          statusCode: 404,
        ),
      );
      await expectLater(
        repository.load('conversation'),
        throwsA(isA<DioException>()),
      );
      expect(
        await local.getConversationHistory('conversation', userId: 'alice'),
        isNull,
      );
      expect(
        await local.getConversationMeta('conversation', userId: 'alice'),
        isNull,
      );
    },
  );

  test('outages allow cached reads but auth failures do not', () async {
    await seed();
    api.failure = DioException(
      requestOptions: RequestOptions(path: '/full'),
      type: DioExceptionType.connectionError,
    );
    expect((await repository.load('conversation')).fromCache, isTrue);
    api.failure = DioException(
      requestOptions: RequestOptions(path: '/full'),
      response: Response(
        requestOptions: RequestOptions(path: '/full'),
        statusCode: 401,
      ),
    );
    await expectLater(
      repository.load('conversation'),
      throwsA(isA<DioException>()),
    );
  });

  test(
    'clearing one account deletes its histories without affecting another account',
    () async {
      await seed();
      await local.saveConversationHistory('conversation', [
        ConversationMessage(
          role: 'user',
          content: 'Bob',
          timestamp: DateTime.utc(2026),
        ),
      ], userId: 'bob');
      await local.clearAll(userId: 'alice');
      expect(
        await local.getConversationHistory('conversation', userId: 'alice'),
        isNull,
      );
      expect(
        await local.getConversationHistory('conversation', userId: 'bob'),
        isNotNull,
      );
    },
  );
}
