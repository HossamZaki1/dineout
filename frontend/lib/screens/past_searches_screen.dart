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
  bool _isSelectionMode = false;
  Set<String> _selectedItems = {};

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

  Widget _buildRestaurantSuggestions(ConversationMeta meta) {
    if (meta.totalRestaurantSuggestions == 0) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.restaurant_menu, size: 16, color: Colors.orange),
              const SizedBox(width: 4),
              Text(
                '${meta.totalRestaurantSuggestions} restaurant${meta.totalRestaurantSuggestions > 1 ? 's' : ''}',
                style: const TextStyle(
                  fontSize: 12,
                  color: Colors.orange,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          // Restaurant photos row
          if (meta.restaurantPhotoUrls.isNotEmpty) ...[
            SizedBox(
              height: 40,
              child: Row(
                children: [
                  // Show up to 4 restaurant photos
                  ...meta.restaurantPhotoUrls
                      .take(4)
                      .map(
                        (photoUrl) => Container(
                          margin: const EdgeInsets.only(right: 4),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: Image.network(
                              photoUrl,
                              width: 40,
                              height: 40,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) =>
                                  Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: Colors.grey[200],
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: const Icon(
                                      Icons.restaurant,
                                      color: Colors.grey,
                                      size: 20,
                                    ),
                                  ),
                            ),
                          ),
                        ),
                      ),
                  // Show count if there are more photos
                  if (meta.restaurantPhotoUrls.length > 4)
                    Container(
                      width: 40,
                      height: 40,
                      margin: const EdgeInsets.only(right: 4),
                      decoration: BoxDecoration(
                        color: Colors.grey[300],
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Center(
                        child: Text(
                          '+${meta.restaurantPhotoUrls.length - 4}',
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: Colors.grey,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 4),
          ],
          // Restaurant names chips
          if (meta.restaurantSuggestionNames.isNotEmpty) ...[
            Wrap(
              spacing: 4,
              runSpacing: 2,
              children:
                  meta.restaurantSuggestionNames.take(3).map((name) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.orange.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: Colors.orange.withOpacity(0.3),
                        ),
                      ),
                      child: Text(
                        name,
                        style: const TextStyle(
                          fontSize: 11,
                          color: Colors.orange,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    );
                  }).toList()..addAll([
                    if (meta.restaurantSuggestionNames.length > 3)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.grey.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: Colors.grey.withOpacity(0.3),
                          ),
                        ),
                        child: Text(
                          '+${meta.restaurantSuggestionNames.length - 3} more',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Colors.grey,
                            fontWeight: FontWeight.w400,
                          ),
                        ),
                      ),
                  ]),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _showDeleteConfirmation(ConversationMeta meta) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Search'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Are you sure you want to delete "${meta.title.isEmpty ? 'Untitled' : meta.title}"?',
            ),
            const SizedBox(height: 8),
            if (meta.totalRestaurantSuggestions > 0) ...[
              Row(
                children: [
                  const Icon(Icons.warning, color: Colors.orange, size: 16),
                  const SizedBox(width: 4),
                  Text(
                    'This includes ${meta.totalRestaurantSuggestions} restaurant suggestion${meta.totalRestaurantSuggestions > 1 ? 's' : ''}',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],
            const Text(
              'This action cannot be undone.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await _delete(meta);
    }
  }

  void _toggleSelectionMode() {
    setState(() {
      _isSelectionMode = !_isSelectionMode;
      if (!_isSelectionMode) {
        _selectedItems.clear();
      }
    });
  }

  void _selectAll() {
    setState(() {
      if (_selectedItems.length == _items.length) {
        _selectedItems.clear();
      } else {
        _selectedItems = _items.map((item) => item.id).toSet();
      }
    });
  }

  Future<void> _deleteSelected() async {
    if (_selectedItems.isEmpty) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Delete ${_selectedItems.length} Search${_selectedItems.length > 1 ? 'es' : ''}',
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Are you sure you want to delete ${_selectedItems.length} conversation${_selectedItems.length > 1 ? 's' : ''}?',
            ),
            const SizedBox(height: 8),
            const Text(
              'This action cannot be undone.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete All'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final userId = _auth.currentUser?.uid;

      // Delete all selected items
      for (final itemId in _selectedItems) {
        final item = _items.firstWhere((item) => item.id == itemId);
        try {
          if (userId != null) {
            await _api.delete(userId, item.id);
          }
        } catch (_) {
          // ignore API delete failure, continue to local
        }
        await _local.deleteConversation(item.id, userId: userId);
      }

      _selectedItems.clear();
      _isSelectionMode = false;
      await _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: _isSelectionMode
            ? Text('${_selectedItems.length} selected')
            : const Text('Past Searches'),
        leading: _isSelectionMode
            ? IconButton(
                icon: const Icon(Icons.close),
                onPressed: _toggleSelectionMode,
              )
            : null,
        actions: _isSelectionMode
            ? [
                IconButton(
                  icon: Icon(
                    _selectedItems.length == _items.length
                        ? Icons.deselect
                        : Icons.select_all,
                  ),
                  onPressed: _selectAll,
                  tooltip: _selectedItems.length == _items.length
                      ? 'Deselect All'
                      : 'Select All',
                ),
                IconButton(
                  icon: const Icon(Icons.delete, color: Colors.red),
                  onPressed: _selectedItems.isNotEmpty ? _deleteSelected : null,
                  tooltip: 'Delete Selected',
                ),
              ]
            : [
                PopupMenuButton<String>(
                  onSelected: (value) {
                    if (value == 'select') {
                      _toggleSelectionMode();
                    }
                  },
                  itemBuilder: (context) => [
                    const PopupMenuItem<String>(
                      value: 'select',
                      child: Row(
                        children: [
                          Icon(Icons.checklist, size: 20),
                          SizedBox(width: 8),
                          Text('Select'),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
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
                  SizedBox(height: 16),
                  Center(
                    child: Text(
                      'Your conversation history will appear here',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ),
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
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: const Icon(Icons.delete, color: Colors.white),
                    ),
                    secondaryBackground: Container(
                      color: Colors.red,
                      alignment: Alignment.centerRight,
                      padding: const EdgeInsets.symmetric(horizontal: 8),
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
                                  onPressed: () =>
                                      Navigator.pop(context, false),
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
                      contentPadding: const EdgeInsets.only(
                        left: 16.0, // Keep left padding
                        right: 8.0, // Reduce right padding from 24 to 8
                        top: 8.0,
                        bottom: 8.0,
                      ),
                      leading: _isSelectionMode
                          ? Checkbox(
                              value: _selectedItems.contains(item.id),
                              onChanged: (selected) {
                                setState(() {
                                  if (selected == true) {
                                    _selectedItems.add(item.id);
                                  } else {
                                    _selectedItems.remove(item.id);
                                  }
                                });
                              },
                            )
                          : item.totalRestaurantSuggestions > 0
                          ? const Icon(Icons.restaurant, color: Colors.orange)
                          : const Icon(Icons.history),
                      title: Text(
                        item.title.isEmpty ? 'Untitled' : item.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${_formatDate(item.updatedAt)} • ${item.lastMessagePreview}',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (item.totalRestaurantSuggestions > 0) ...[
                            const SizedBox(height: 4),
                            _buildRestaurantSuggestions(item),
                          ],
                        ],
                      ),
                      trailing: _isSelectionMode
                          ? null
                          : PopupMenuButton<String>(
                              icon: const Icon(
                                Icons.more_vert,
                                color: Colors.grey,
                              ),
                              padding: EdgeInsets.all(0),
                              onSelected: (value) async {
                                if (value == 'delete') {
                                  await _showDeleteConfirmation(item);
                                }
                              },
                              itemBuilder: (context) => [
                                const PopupMenuItem<String>(
                                  value: 'delete',
                                  child: Row(
                                    children: [
                                      Icon(
                                        Icons.delete,
                                        color: Colors.red,
                                        size: 20,
                                      ),
                                      SizedBox(width: 8),
                                      Text(
                                        'Delete',
                                        style: TextStyle(color: Colors.red),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                      onTap: () async {
                        if (_isSelectionMode) {
                          setState(() {
                            if (_selectedItems.contains(item.id)) {
                              _selectedItems.remove(item.id);
                            } else {
                              _selectedItems.add(item.id);
                            }
                          });
                        } else {
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
                        }
                      },
                    ),
                  );
                },
              ),
      ),
    );
  }
}
