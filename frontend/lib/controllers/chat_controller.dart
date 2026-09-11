import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../models/chat.dart';
import '../services/conversation_repository.dart';

/// Owns chat state and request lifetime, independent of widgets and speech.
class ChatController extends ChangeNotifier {
  final ChatRepository repository;
  final String sessionId;
  final List<Message> _messages = [];
  CancelToken? _request;
  bool _disposed = false;
  bool isBusy = false;
  String? error;
  String? notice;

  ChatController({
    required this.repository,
    required this.sessionId,
    bool existing = false,
  }) {
    if (!existing) {
      _messages.add(
        const Message(
          text:
              'Hi! I can help you find a great place to eat. Where are you looking for restaurants?',
          isUser: false,
        ),
      );
    }
  }

  List<Message> get messages => List.unmodifiable(_messages);

  Future<void> load() async {
    if (_disposed || isBusy) return;
    isBusy = true;
    error = null;
    _request = CancelToken();
    notifyListeners();
    try {
      final result = await repository.load(sessionId, cancelToken: _request);
      if (_disposed) return;
      _messages
        ..clear()
        ..addAll(result.messages.reversed.map(Message.fromStored));
      notice = result.fromCache
          ? 'Showing saved history. Reconnect to send messages.'
          : null;
    } catch (failure) {
      if (!_disposed &&
          !(failure is DioException && CancelToken.isCancel(failure))) {
        error = conversationError(failure);
      }
    } finally {
      if (!_disposed) {
        isBusy = false;
        notifyListeners();
      }
    }
  }

  Future<ChatReply?> send(String input) async {
    final text = input.trim();
    if (_disposed || isBusy || text.isEmpty) return null;
    final history = _messages
        .take(10)
        .toList()
        .reversed
        .map(
          (message) => {
            'role': message.isUser ? 'user' : 'assistant',
            'content': message.text,
          },
        )
        .toList();
    final userMessage = Message(text: text);
    _messages.insert(0, userMessage);
    isBusy = true;
    error = null;
    notice = null;
    _request = CancelToken();
    notifyListeners();
    try {
      final reply = await repository.send(
        sessionId,
        text,
        history,
        cancelToken: _request,
      );
      if (_disposed) return null;
      _messages.insert(
        0,
        Message(
          text: reply.text,
          isUser: false,
          restaurants: reply.suggestions.map(RestaurantInfo.fromJson).toList(),
          wasSearchRequest: reply.searchPerformed,
        ),
      );
      return reply;
    } catch (failure) {
      if (!_disposed) {
        _messages.remove(userMessage);
        if (!(failure is DioException && CancelToken.isCancel(failure))) {
          error = conversationError(failure);
        }
      }
      return null;
    } finally {
      if (!_disposed) {
        isBusy = false;
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _request?.cancel('Chat screen closed');
    super.dispose();
  }
}
