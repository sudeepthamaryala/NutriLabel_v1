// lib/shared/providers/history_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/chat.dart';
import '../services/api_service.dart';

class HistoryState {
  final List<ChatSession> sessions;
  final bool isLoading;
  final String? error;

  const HistoryState({
    this.sessions = const [],
    this.isLoading = false,
    this.error,
  });

  HistoryState copyWith({
    List<ChatSession>? sessions,
    bool? isLoading,
    String? error,
  }) =>
      HistoryState(
        sessions: sessions ?? this.sessions,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

class HistoryNotifier extends StateNotifier<HistoryState> {
  HistoryNotifier() : super(const HistoryState());

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final sessions = await ApiService.instance.getChatSessions();
      // Most recent first
      sessions.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      state = HistoryState(sessions: sessions);
    } catch (e) {
      state = HistoryState(
        error: e.toString().replaceFirst('Exception: ', ''),
      );
    }
  }

  /// Group sessions by date for the History screen
  Map<String, List<ChatSession>> get grouped {
    final Map<String, List<ChatSession>> result = {};
    for (final session in state.sessions) {
      final date = _formatDate(session.createdAt);
      result.putIfAbsent(date, () => []).add(session);
    }
    return result;
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(dt.year, dt.month, dt.day);
    final diff = today.difference(d).inDays;
    if (diff == 0) return 'Today';
    if (diff == 1) return 'Yesterday';
    return '${dt.day}/${dt.month}/${dt.year}';
  }
}

final historyProvider =
    StateNotifierProvider<HistoryNotifier, HistoryState>((ref) => HistoryNotifier());
