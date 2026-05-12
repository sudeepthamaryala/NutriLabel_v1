// lib/features/compare/compare_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import '../../app/theme.dart';
import '../../shared/providers/compare_provider.dart';
import '../../shared/widgets/common_app_bar.dart';
import '../../shared/widgets/cross_platform_image.dart';
import '../../shared/widgets/loading_overlay.dart';

class CompareScreen extends ConsumerStatefulWidget {
  const CompareScreen({super.key});
  @override
  ConsumerState<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends ConsumerState<CompareScreen> {
  final _picker = ImagePicker();
  final _questionCtrl = TextEditingController();

  @override
  void dispose() { _questionCtrl.dispose(); super.dispose(); }

  Future<void> _pick() async {
    final x = await _picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (x == null) return;
    // PickedImage.fromXFile handles platform differences:
    //   Web   → reads bytes via x.readAsBytes()
    //   Mobile → wraps path in dart:io File
    final picked = await PickedImage.fromXFile(x);
    ref.read(compareProvider.notifier).addImage(picked);
  }

  Future<void> _compare() async {
    await ref.read(compareProvider.notifier).compare(question: _questionCtrl.text.trim());
    final err = ref.read(compareProvider).error;
    if (err != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err), backgroundColor: AppTheme.error));
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(compareProvider);
    return LoadingOverlay(
      isLoading: state.isLoading,
      message: 'Comparing products…',
      child: Scaffold(
        backgroundColor: AppTheme.surface,
        appBar: CommonAppBar(
          title: 'Compare Products',
          showBackButton: true,
          actions: [if (state.result != null) IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: () => ref.read(compareProvider.notifier).reset())],
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Add Products (2–5)', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            const Text('Upload nutrition label photos to compare', style: TextStyle(color: AppTheme.onSurfaceMuted, fontSize: 13)),
            const SizedBox(height: 16),
            _ImageGrid(images: state.images, onAdd: state.images.length < 5 ? _pick : null, onRemove: (i) => ref.read(compareProvider.notifier).removeImage(i)),
            const SizedBox(height: 20),
            TextField(controller: _questionCtrl, decoration: const InputDecoration(labelText: 'Question (optional)', hintText: 'e.g. Which has less sugar?', prefixIcon: Icon(Icons.help_outline_rounded))),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: state.images.length >= 2 && !state.isLoading ? _compare : null,
              icon: const Icon(Icons.compare_arrows_rounded),
              label: Text('Compare ${state.images.length} Products'),
              style: FilledButton.styleFrom(minimumSize: const Size(double.infinity, 52)),
            ),
            if (state.result != null) ...[const SizedBox(height: 28), _ResultCard(result: state.result!)],
            if (state.images.isEmpty)
              const Padding(padding: EdgeInsets.symmetric(vertical: 32), child: Center(child: Text('Add at least 2 product images to compare', textAlign: TextAlign.center, style: TextStyle(color: AppTheme.onSurfaceMuted)))),
          ]),
        ),
      ),
    );
  }
}

class _ImageGrid extends StatelessWidget {
  final List<PickedImage> images;
  final VoidCallback? onAdd;
  final ValueChanged<int> onRemove;
  const _ImageGrid({required this.images, required this.onAdd, required this.onRemove});
  @override
  Widget build(BuildContext context) {
    return Wrap(spacing: 10, runSpacing: 10, children: [
      ...images.asMap().entries.map((e) => Stack(children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: CrossPlatformImage(
            file: e.value.file,
            bytes: e.value.bytes,
            width: 90,
            height: 90,
            fit: BoxFit.cover,
          ),
        ),
        Positioned(top: 4, left: 4, child: Container(width: 20, height: 20, decoration: const BoxDecoration(color: AppTheme.primary, shape: BoxShape.circle), child: Center(child: Text('${e.key + 1}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700))))),
        Positioned(top: 2, right: 2, child: GestureDetector(onTap: () => onRemove(e.key), child: Container(width: 22, height: 22, decoration: const BoxDecoration(color: AppTheme.error, shape: BoxShape.circle), child: const Icon(Icons.close, color: Colors.white, size: 12)))),
      ])),
      if (onAdd != null)
        GestureDetector(onTap: onAdd, child: Container(width: 90, height: 90, decoration: BoxDecoration(color: AppTheme.primary.withOpacity(0.08), borderRadius: BorderRadius.circular(12), border: Border.all(color: AppTheme.primary.withOpacity(0.4))), child: const Icon(Icons.add_photo_alternate_rounded, color: AppTheme.primary, size: 32))),
    ]);
  }
}

class _ResultCard extends StatelessWidget {
  final dynamic result;
  const _ResultCard({required this.result});
  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Comparison Result', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      const SizedBox(height: 12),
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(gradient: const LinearGradient(colors: [AppTheme.primary, AppTheme.primaryLight]), borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          const Icon(Icons.emoji_events_rounded, color: AppTheme.accent, size: 32),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Best Choice', style: TextStyle(color: Colors.white70, fontSize: 12)),
            Text('Product ${result.bestProductIndex + 1}', style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700)),
          ])),
        ]),
      ),
      const SizedBox(height: 16),
      if ((result.verdict.reasons as List).isNotEmpty) _BulletSection('✅ Why it\'s best', result.verdict.reasons, AppTheme.success),
      if ((result.verdict.tradeoffs as List).isNotEmpty) _BulletSection('⚖️ Tradeoffs', result.verdict.tradeoffs, AppTheme.warning),
      if ((result.verdict.warnings as List).isNotEmpty) _BulletSection('⚠️ Watch out', result.verdict.warnings, AppTheme.error),
    ]);
  }
}

class _BulletSection extends StatelessWidget {
  final String title;
  final List items;
  final Color color;
  const _BulletSection(this.title, this.items, this.color);
  @override
  Widget build(BuildContext context) {
    return Padding(padding: const EdgeInsets.only(bottom: 14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title, style: TextStyle(fontWeight: FontWeight.w700, color: color, fontSize: 14)),
      const SizedBox(height: 6),
      ...items.map((i) => Padding(padding: const EdgeInsets.only(bottom: 4), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(margin: const EdgeInsets.only(top: 6, right: 8), width: 5, height: 5, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        Expanded(child: Text(i.toString(), style: const TextStyle(fontSize: 13, height: 1.4))),
      ]))),
    ]));
  }
}
