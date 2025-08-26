import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../services/conversation_service.dart';
import '../services/conversations_api_service.dart';
import '../models/conversation.dart';
import '../chat_screen.dart';

class PastSearchesScreen extends StatefulWidget {
  const PastSearchesScreen({super.key});

  @override
  State<PastSearchesScreen> createState() => _PastSearchesScreenState();
}

class _PastSearchesScreenState extends State<PastSearchesScreen> {
  final _auth = AuthService();
  final _local = ConversationService();
  final _api = ConversationsApiService();
  List<ConversationMeta> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final userId = _auth.currentUser?.uid;
    try {
      if (userId != null) {
        // Prefer backend when signed in
        final data = await _api.listConversations(userId);
        setState(() {
          _items = data;
          _loading = false;
        });
        // Also sync locally as cache (best-effort)
        for (final m in data) {
          await _local.upsertConversation(m, userId: userId);
        }
        return;
      }
    } catch (_) {
      // fallback to local
    }
    final data = await _local.getConversations(userId: userId);
    setState(() {
      _items = data;
      _loading = false;
    });
  }

  String _formatDate(DateTime dt) {
    final y = dt.year.toString().padLeft(4, '0');
    final m = dt.month.toString().padLeft(2, '0');
    final d = dt.day.toString().padLeft(2, '0');
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');
    return '$y-$m-$d $hh:$mm';
  }

  Future<void> _delete(ConversationMeta meta) async {
    final userId = _auth.currentUser?.uid;
    try {
      if (userId != null) {
        await _api.delete(userId, meta.id);
      }
    } catch (_) {
      // ignore API delete failure, continue to local
    }
    await _local.deleteConversation(meta.id, userId: userId);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Past Searches'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _items.isEmpty
                ? ListView(
                    children: const [
                      SizedBox(height: 120),
                      Center(child: Text('No past searches yet.')),
                    ],
                  )
                : ListView.separated(
                    itemCount: _items.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final item = _items[index];
                      return Dismissible(
                        key: ValueKey(item.id),
                        background: Container(
                          color: Colors.red,
                          alignment: Alignment.centerLeft,
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: const Icon(Icons.delete, color: Colors.white),
                        ),
                        secondaryBackground: Container(
                          color: Colors.red,
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: const Icon(Icons.delete, color: Colors.white),
                        ),
                        confirmDismiss: (_) async {
                          return await showDialog<bool>(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: const Text('Delete conversation?'),
                                  content: const Text('This cannot be undone.'),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.pop(context, false),
                                      child: const Text('Cancel'),
                                    ),
                                    TextButton(
                                      onPressed: () => Navigator.pop(context, true),
                                      child: const Text('Delete'),
                                    ),
                                  ],
                                ),
                              ) ??
                              false;
                        },
                        onDismissed: (_) => _delete(item),
                        child: ListTile(
                          leading: const Icon(Icons.history),
                          title: Text(
                            item.title.isEmpty ? 'Untitled' : item.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(
                            '${_formatDate(item.updatedAt)} • ${item.lastMessagePreview}',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          onTap: () async {
                            await Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => ChatScreen(
                                  sessionId: item.id,
                                  initialTitle: item.title,
                                ),
                              ),
                            );
                            await _load();
                          },
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}
