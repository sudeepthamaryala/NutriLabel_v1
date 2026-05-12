// lib/shared/widgets/chat_bubble.dart
import 'package:flutter/material.dart';

import '../../app/theme.dart';

enum BubbleRole { user, assistant }

class ChatBubble extends StatelessWidget {
  final String message;
  final BubbleRole role;
  final String? imageUrl;
  final DateTime? timestamp;

  const ChatBubble({
    super.key,
    required this.message,
    required this.role,
    this.imageUrl,
    this.timestamp,
  });

  bool get isUser => role == BubbleRole.user;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) _Avatar(),
          const SizedBox(width: 8),
          Flexible(
            child: Column(
              crossAxisAlignment: isUser
                  ? CrossAxisAlignment.end
                  : CrossAxisAlignment.start,
              children: [
                if (imageUrl != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      imageUrl!,
                      width: 180,
                      height: 180,
                      fit: BoxFit.cover,
                    ),
                  ),
                Container(
                  margin: imageUrl != null
                      ? const EdgeInsets.only(top: 4)
                      : EdgeInsets.zero,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: isUser ? AppTheme.primary : Colors.white,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(16),
                      topRight: const Radius.circular(16),
                      bottomLeft: Radius.circular(isUser ? 16 : 4),
                      bottomRight: Radius.circular(isUser ? 4 : 16),
                    ),
                    border: isUser
                        ? null
                        : Border.all(color: AppTheme.divider),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.06),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Text(
                    message,
                    style: TextStyle(
                      fontSize: 14,
                      color: isUser ? Colors.white : AppTheme.onSurface,
                      height: 1.4,
                    ),
                  ),
                ),
                if (timestamp != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4, left: 4, right: 4),
                    child: Text(
                      _formatTime(timestamp!),
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppTheme.onSurfaceMuted,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (isUser) _Avatar(isUser: true),
        ],
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

class _Avatar extends StatelessWidget {
  final bool isUser;
  const _Avatar({this.isUser = false});

  @override
  Widget build(BuildContext context) {
    return CircleAvatar(
      radius: 14,
      backgroundColor: isUser ? AppTheme.accent : AppTheme.primary,
      child: Icon(
        isUser ? Icons.person_rounded : Icons.eco_rounded,
        color: Colors.white,
        size: 14,
      ),
    );
  }
}
