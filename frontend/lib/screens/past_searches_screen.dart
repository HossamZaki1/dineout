import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import '../services/conversation_service.dart';
import '../services/conversations_api_service.dart';
import '../services/conversation_repository.dart';
import '../models/conversation.dart';
import '../chat_screen.dart';
import '../widgets/restaurant_photo.dart';

class PastSearchesScreen extends StatefulWidget {
  const PastSearchesScreen({super.key});
  @override
  State<PastSearchesScreen> createState() => _PastSearchesScreenState();
}

class _PastSearchesScreenState extends State<PastSearchesScreen> {
  final _auth = AuthService();
  final _local = ConversationService();
  final _api = ConversationsApiService();
  final _selected = <String>{};
  List<ConversationMeta> _items = [];
  String? _nextCursor;
  String? _notice;
  bool _loading = false;
  bool _loadingMore = false;
  bool _deleting = false;
  bool _selecting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool more = false}) async {
    if (_loading || _loadingMore) return;
    final userId = _auth.currentUser?.uid;
    if (userId == null) return;
    setState(() {
      if (more) {
        _loadingMore = true;
      } else {
        _loading = true;
      }
      _notice = null;
    });
    try {
      var page = await _api.listPage(cursor: more ? _nextCursor : null);
      // A page may contain only deletion markers; its cursor still advances.
      while (page.items.isEmpty && page.nextCursor != null) {
        page = await _api.listPage(cursor: page.nextCursor);
      }
      if (!mounted || _auth.currentUser?.uid != userId) return;
      setState(() {
        if (more) {
          final ids = _items.map((m) => m.id).toSet();
          _items.addAll(page.items.where((m) => !ids.contains(m.id)));
        } else {
          _items = page.items;
          _selected.clear();
        }
        _nextCursor = page.nextCursor;
      });
      try {
        for (final item in page.items) {
          await _local.upsertConversation(item, userId: userId);
        }
      } catch (_) {
        /* The server list remains usable if the cache is unavailable. */
      }
    } catch (error) {
      if (!mounted || _auth.currentUser?.uid != userId) return;
      var usedCache = false;
      if (!more && _items.isEmpty && canUseConversationCache(error)) {
        try {
          final cached = await _local.getConversations(userId: userId);
          if (!mounted || _auth.currentUser?.uid != userId) return;
          setState(() {
            _items = cached;
            _nextCursor = null;
          });
          usedCache = cached.isNotEmpty;
        } catch (_) {}
      }
      if (mounted) {
        setState(() {
          _notice =
              '${conversationError(error)}${usedCache ? ' Showing saved history.' : ''}';
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadingMore = false;
        });
      }
    }
  }

  Future<bool> _confirmDelete(String label) async =>
      await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Delete conversation?'),
          content: Text('Delete $label and its messages?'),
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

  Future<bool> _delete(ConversationMeta item, {bool remove = true}) async {
    final userId = _auth.currentUser?.uid;
    if (userId == null) return false;
    try {
      await _api.delete(item.id);
      try {
        await _local.deleteConversation(item.id, userId: userId);
      } catch (_) {}
      if (!mounted || _auth.currentUser?.uid != userId) return false;
      if (remove) {
        setState(() {
          _items.removeWhere((m) => m.id == item.id);
          _selected.remove(item.id);
        });
      }
      return true;
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Deletion failed. ${conversationError(error)}'),
          ),
        );
      }
      return false;
    }
  }

  Future<void> _deleteSelected() async {
    if (_deleting || _selected.isEmpty) return;
    if (!await _confirmDelete('${_selected.length} conversations') ||
        !mounted) {
      return;
    }
    setState(() => _deleting = true);
    final items = _items.where((m) => _selected.contains(m.id)).toList();
    try {
      for (final item in items) {
        if (!mounted) break;
        await _delete(item);
      }
    } finally {
      if (mounted) {
        setState(() {
          _deleting = false;
          _selecting = _selected.isNotEmpty;
        });
      }
    }
  }

  Future<void> _rename(ConversationMeta item) async {
    final userId = _auth.currentUser?.uid;
    if (userId == null) return;
    var draft = item.title;
    final title = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename conversation'),
        content: TextFormField(
          initialValue: item.title,
          maxLength: 100,
          autofocus: true,
          onChanged: (value) => draft = value,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              if (draft.trim().isNotEmpty) {
                Navigator.pop(context, draft.trim());
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (!mounted || title == null || _auth.currentUser?.uid != userId) return;
    try {
      final updated = await _api.updateTitle(item.id, title);
      if (!mounted || _auth.currentUser?.uid != userId) return;
      try {
        await _local.upsertConversation(updated, userId: userId);
      } catch (_) {}
      if (mounted) {
        setState(() {
          final index = _items.indexWhere((m) => m.id == item.id);
          if (index >= 0) _items[index] = updated;
        });
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(conversationError(error))));
      }
    }
  }

  void _toggle(ConversationMeta item) => setState(() {
    if (!_selected.add(item.id)) _selected.remove(item.id);
  });

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(
        _selecting ? '${_selected.length} selected' : 'Past Searches',
      ),
      actions: [
        if (_selecting) ...[
          IconButton(
            tooltip: 'Select loaded searches',
            icon: const Icon(Icons.select_all),
            onPressed: _deleting
                ? null
                : () =>
                      setState(() => _selected.addAll(_items.map((m) => m.id))),
          ),
          IconButton(
            tooltip: 'Delete selected',
            icon: const Icon(Icons.delete),
            onPressed: _deleting || _selected.isEmpty ? null : _deleteSelected,
          ),
        ],
        IconButton(
          tooltip: _selecting ? 'Cancel selection' : 'Select searches',
          icon: Icon(_selecting ? Icons.close : Icons.checklist),
          onPressed: _deleting
              ? null
              : () => setState(() {
                  _selecting = !_selecting;
                  _selected.clear();
                }),
        ),
      ],
    ),
    body: Column(
      children: [
        if (_notice != null)
          Padding(padding: const EdgeInsets.all(8), child: Text(_notice!)),
        if (_deleting) const LinearProgressIndicator(),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () => _load(),
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    itemCount: _items.isEmpty
                        ? 1
                        : _items.length + (_nextCursor == null ? 0 : 1),
                    separatorBuilder: (context, index) =>
                        const Divider(height: 1),
                    itemBuilder: (context, index) {
                      if (_items.isEmpty) {
                        return const Padding(
                          padding: EdgeInsets.all(40),
                          child: Center(child: Text('No past searches yet.')),
                        );
                      }
                      if (index == _items.length) {
                        return TextButton(
                          onPressed: _loadingMore
                              ? null
                              : () => _load(more: true),
                          child: Text(_loadingMore ? 'Loading…' : 'Load more'),
                        );
                      }
                      final item = _items[index];
                      return Dismissible(
                        key: ValueKey(item.id),
                        direction: _selecting || _deleting
                            ? DismissDirection.none
                            : DismissDirection.endToStart,
                        background: Container(
                          color: Colors.red,
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.all(16),
                          child: const Icon(Icons.delete, color: Colors.white),
                        ),
                        confirmDismiss: (direction) async {
                          if (!await _confirmDelete(item.title) || !mounted) {
                            return false;
                          }
                          return _delete(item, remove: false);
                        },
                        onDismissed: (direction) => setState(
                          () => _items.removeWhere((m) => m.id == item.id),
                        ),
                        child: ListTile(
                          leading: _selecting
                              ? Checkbox(
                                  value: _selected.contains(item.id),
                                  onChanged: _deleting
                                      ? null
                                      : (_) => _toggle(item),
                                )
                              : const Icon(Icons.history),
                          title: Text(
                            item.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.lastMessagePreview,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              Text(
                                item.updatedAt.toLocal().toString().substring(
                                  0,
                                  16,
                                ),
                              ),
                              if (item.totalRestaurantSuggestions > 0)
                                Text(
                                  '${item.totalRestaurantSuggestions} restaurant suggestions',
                                ),
                              if (item.restaurantPhotoUrls.isNotEmpty)
                                SizedBox(
                                  height: 40,
                                  child: Row(
                                    children: item.restaurantPhotoUrls
                                        .take(4)
                                        .map(
                                          (url) => Padding(
                                            padding: const EdgeInsets.only(
                                              right: 4,
                                            ),
                                            child: RestaurantPhoto(
                                              reference: url,
                                              width: 40,
                                              height: 40,
                                            ),
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ),
                            ],
                          ),
                          trailing: _selecting
                              ? null
                              : PopupMenuButton<String>(
                                  enabled: !_deleting,
                                  onSelected: (action) async {
                                    if (action == 'rename') {
                                      await _rename(item);
                                    } else if (await _confirmDelete(
                                          item.title,
                                        ) &&
                                        mounted) {
                                      await _delete(item);
                                    }
                                  },
                                  itemBuilder: (context) => const [
                                    PopupMenuItem(
                                      value: 'rename',
                                      child: Text('Rename'),
                                    ),
                                    PopupMenuItem(
                                      value: 'delete',
                                      child: Text('Delete'),
                                    ),
                                  ],
                                ),
                          onTap: _deleting
                              ? null
                              : () async {
                                  if (_selecting) {
                                    _toggle(item);
                                    return;
                                  }
                                  await Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => ChatScreen(
                                        sessionId: item.id,
                                        initialTitle: item.title,
                                      ),
                                    ),
                                  );
                                  if (mounted) await _load();
                                },
                        ),
                      );
                    },
                  ),
          ),
        ),
      ],
    ),
  );
}
