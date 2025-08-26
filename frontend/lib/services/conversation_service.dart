// filepath: /Users/hossamzaki/StudioProjects/dineout/frontend/lib/services/conversation_service.dart
import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';
import '../models/conversation.dart';

class ConversationService {
  static const _storageKeyPrefix = 'conversations:'; // key per user

  String _keyForUser(String? userId) => '$_storageKeyPrefix${userId ?? 'guest'}';

  Future<List<ConversationMeta>> getConversations({String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    final raw = prefs.getString(key);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List list = json.decode(raw) as List;
      return list
          .map((e) => ConversationMeta.fromMap(e as Map<String, dynamic>))
          .toList()
        ..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    } catch (_) {
      return [];
    }
  }

  Future<void> upsertConversation(ConversationMeta meta, {String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    final existing = await getConversations(userId: userId);
    final idx = existing.indexWhere((c) => c.id == meta.id);
    if (idx >= 0) {
      // Preserve createdAt
      final current = existing[idx];
      existing[idx] = meta.copyWith(createdAt: current.createdAt);
    } else {
      existing.add(meta);
    }
    final encoded = json.encode(existing.map((e) => e.toMap()).toList());
    await prefs.setString(key, encoded);
  }

  Future<void> deleteConversation(String id, {String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    final existing = await getConversations(userId: userId);
    existing.removeWhere((c) => c.id == id);
    final encoded = json.encode(existing.map((e) => e.toMap()).toList());
    await prefs.setString(key, encoded);
  }

  Future<void> clearAll({String? userId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _keyForUser(userId);
    await prefs.remove(key);
  }
}

