// lib/features/history/history_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/theme.dart';
import '../../shared/models/chat.dart';
import '../../shared/providers/history_provider.dart';
import '../../shared/widgets/bottom_nav_bar.dart';
import '../../shared/widgets/common_app_bar.dart';

class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});
  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(historyProvider.notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(historyProvider);
    final notifier = ref.read(historyProvider.notifier);

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: const CommonAppBar(title: 'History'),
      bottomNavigationBar: const AppBottomNavBar(currentIndex: 1),
      body: Builder(builder: (_) {
        if (state.isLoading) {
          return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
        }
        if (state.error != null) {
          return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.wifi_off_rounded, size: 48, color: AppTheme.onSurfaceMuted),
            const SizedBox(height: 12),
            Text(state.error!, textAlign: TextAlign.center, style: const TextStyle(color: AppTheme.onSurfaceMuted)),
            const SizedBox(height: 16),
            TextButton.icon(icon: const Icon(Icons.refresh), label: const Text('Retry'), onPressed: () => ref.read(historyProvider.notifier).load()),
          ]));
        }
        if (state.sessions.isEmpty) {
          return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.history_rounded, size: 64, color: AppTheme.onSurfaceMuted.withOpacity(0.4)),
            const SizedBox(height: 16),
            const Text('No history yet', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: AppTheme.onSurfaceMuted)),
            const SizedBox(height: 8),
            const Text('Analyses and comparisons will appear here', style: TextStyle(color: AppTheme.onSurfaceMuted, fontSize: 13)),
            const SizedBox(height: 24),
            FilledButton.icon(icon: const Icon(Icons.camera_alt_rounded), label: const Text('Analyse a Label'), onPressed: () => context.push('/analyse')),
          ]));
        }

        final grouped = notifier.grouped;
        final dateKeys = grouped.keys.toList();

        return RefreshIndicator(
          color: AppTheme.primary,
          onRefresh: () => ref.read(historyProvider.notifier).load(),
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: dateKeys.length,
            itemBuilder: (_, i) {
              final date = dateKeys[i];
              final sessions = grouped[date]!;
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Padding(
                  padding: const EdgeInsets.only(bottom: 10, top: 8),
                  child: Text(date, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.onSurfaceMuted, letterSpacing: 0.5)),
                ),
                ...sessions.map((s) => _SessionTile(session: s)),
                const SizedBox(height: 8),
              ]);
            },
          ),
        );
      }),
    );
  }
}

class _SessionTile extends StatelessWidget {
  final ChatSession session;
  const _SessionTile({required this.session});

  @override
  Widget build(BuildContext context) {
    final isAnalyse = session.type == ChatSessionType.analyse;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          width: 44, height: 44,
          decoration: BoxDecoration(
            color: (isAnalyse ? AppTheme.primary : AppTheme.accent).withOpacity(0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(isAnalyse ? Icons.camera_alt_rounded : Icons.compare_arrows_rounded, color: isAnalyse ? AppTheme.primary : AppTheme.accent, size: 22),
        ),
        title: Text(session.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            _formatTime(session.createdAt),
            style: const TextStyle(fontSize: 12, color: AppTheme.onSurfaceMuted),
          ),
        ),
        trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 13, color: AppTheme.onSurfaceMuted),
        onTap: () {
          // Navigate to the appropriate screen
          if (isAnalyse) {
            context.push('/analyse');
          } else {
            context.push('/compare');
          }
        },
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}
