// filepath: /Users/hossamzaki/StudioProjects/dineout/frontend/lib/models/conversation.dart
import 'dart:convert';

class ConversationMeta {
  final String id; // sessionId
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String lastMessagePreview;

  ConversationMeta({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
    required this.lastMessagePreview,
  });

  ConversationMeta copyWith({
    String? id,
    String? title,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? lastMessagePreview,
  }) {
    return ConversationMeta(
      id: id ?? this.id,
      title: title ?? this.title,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      lastMessagePreview: lastMessagePreview ?? this.lastMessagePreview,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'title': title,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'lastMessagePreview': lastMessagePreview,
    };
  }

  factory ConversationMeta.fromMap(Map<String, dynamic> map) {
    return ConversationMeta(
      id: map['id'] as String,
      title: map['title'] as String,
      createdAt: DateTime.parse(map['createdAt'] as String),
      updatedAt: DateTime.parse(map['updatedAt'] as String),
      lastMessagePreview: (map['lastMessagePreview'] ?? '') as String,
    );
  }

  String toJson() => json.encode(toMap());

  factory ConversationMeta.fromJson(String source) => ConversationMeta.fromMap(json.decode(source) as Map<String, dynamic>);
}

