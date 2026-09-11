import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/chat_screen.dart';
import 'package:frontend/controllers/chat_controller.dart';
import 'package:frontend/models/chat.dart';
import 'package:frontend/services/conversation_repository.dart';

class FakeRepository implements ChatRepository {
  final result = Completer<ChatReply>();
  int calls = 0;
  List<Map<String, String>>? history;
  CancelToken? cancelToken;
  @override
  Future<LoadedConversation> load(
    String sessionId, {
    CancelToken? cancelToken,
  }) async => const LoadedConversation([]);
  @override
  Future<ChatReply> send(
    String sessionId,
    String text,
    List<Map<String, String>> history, {
    CancelToken? cancelToken,
  }) {
    calls++;
    this.history = history;
    this.cancelToken = cancelToken;
    return result.future;
  }
}

void main() {
  test(
    'overlapping submissions are rejected and current input is not repeated in history',
    () async {
      final repository = FakeRepository();
      final controller = ChatController(
        repository: repository,
        sessionId: 'session',
      );
      final first = controller.send('Pizza in Berlin');
      expect(controller.isBusy, isTrue);
      expect(await controller.send('Second request'), isNull);
      expect(repository.calls, 1);
      expect(
        repository.history!.where((m) => m['content'] == 'Pizza in Berlin'),
        isEmpty,
      );
      repository.result.complete(
        const ChatReply(text: 'Here are some options'),
      );
      await first;
      expect(controller.messages.first.text, 'Here are some options');
      expect(controller.isBusy, isFalse);
      controller.dispose();
    },
  );

  test('disposing cancels requests and ignores late replies', () async {
    final repository = FakeRepository();
    final controller = ChatController(
      repository: repository,
      sessionId: 'session',
    );
    var notifications = 0;
    controller.addListener(() => notifications++);
    final pending = controller.send('Pizza');
    controller.dispose();
    expect(repository.cancelToken!.isCancelled, isTrue);
    final before = notifications;
    repository.result.complete(const ChatReply(text: 'Late reply'));
    expect(await pending, isNull);
    expect(notifications, before);
  });

  test('failed requests do not become conversation history', () async {
    final repository = FakeRepository();
    final controller = ChatController(
      repository: repository,
      sessionId: 'session',
    );
    final pending = controller.send('Pizza');
    repository.result.completeError(
      DioException(
        requestOptions: RequestOptions(path: '/chat'),
        type: DioExceptionType.connectionError,
      ),
    );
    await pending;
    expect(controller.error, isNotNull);
    expect(controller.messages.where((m) => m.isUser), isEmpty);
    expect(controller.isBusy, isFalse);
    controller.dispose();
  });

  testWidgets(
    'leaving the screen while a reply is pending does not call setState after dispose',
    (tester) async {
      final repository = FakeRepository();
      final controller = ChatController(
        repository: repository,
        sessionId: 'session',
      );
      await tester.pumpWidget(
        MaterialApp(home: ChatScreen(controller: controller)),
      );
      await tester.enterText(find.byType(TextField), 'Pizza');
      await tester.tap(find.byTooltip('Send'));
      await tester.pump();
      await tester.pump();
      expect(repository.calls, 1);
      expect(
        tester
            .widget<IconButton>(
              find.byWidgetPredicate(
                (widget) => widget is IconButton && widget.tooltip == 'Send',
              ),
            )
            .onPressed,
        isNull,
      );
      await tester.pumpWidget(const MaterialApp(home: SizedBox()));
      repository.result.complete(const ChatReply(text: 'Late reply'));
      await tester.pump();
      expect(tester.takeException(), isNull);
    },
  );
}
