// lib/features/analyse/analyse_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../app/theme.dart';
import '../../shared/models/chat.dart';
import '../../shared/providers/analyse_provider.dart';
import '../../shared/widgets/chat_bubble.dart';
import '../../shared/widgets/common_app_bar.dart';
import '../../shared/widgets/cross_platform_image.dart';
import '../../shared/widgets/loading_overlay.dart';

class AnalyseScreen extends ConsumerStatefulWidget {
  const AnalyseScreen({super.key});
  @override
  ConsumerState<AnalyseScreen> createState() => _AnalyseScreenState();
}

class _AnalyseScreenState extends ConsumerState<AnalyseScreen> {
  final _questionCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final _picker = ImagePicker();
  bool _hasAnalysed = false;

  @override
  void dispose() {
    _questionCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    final xfile = await _picker.pickImage(source: source, imageQuality: 85);
    if (xfile == null) return;
    // PickedImage.fromXFile handles platform differences:
    //   Web   → reads bytes via xfile.readAsBytes()
    //   Mobile → wraps path in dart:io File
    final picked = await PickedImage.fromXFile(xfile);
    ref.read(analyseProvider.notifier).setImage(picked);
    setState(() => _hasAnalysed = false);
  }

  Future<void> _analyse() async {
    await ref.read(analyseProvider.notifier).analyse(question: _questionCtrl.text.trim());
    final err = ref.read(analyseProvider).error;
    if (err != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err), backgroundColor: AppTheme.error),
      );
    } else {
      setState(() => _hasAnalysed = true);
      _questionCtrl.clear();
      await Future.delayed(const Duration(milliseconds: 300));
      _scrollCtrl.animateTo(
        _scrollCtrl.position.maxScrollExtent,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOut,
      );
    }
  }

  void _reset() {
    ref.read(analyseProvider.notifier).reset();
    setState(() => _hasAnalysed = false);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(analyseProvider);

    return LoadingOverlay(
      isLoading: state.isLoading,
      message: 'Analysing label…',
      child: Scaffold(
        backgroundColor: AppTheme.surface,
        appBar: CommonAppBar(
          title: 'Analyse Label',
          showBackButton: true,
          actions: [
            if (_hasAnalysed)
              IconButton(
                icon: const Icon(Icons.refresh_rounded),
                onPressed: _reset,
                tooltip: 'Start over',
              ),
          ],
        ),
        body: Column(
          children: [
            Expanded(
              child: state.selectedImage == null
                  ? _EmptyState(onCamera: () => _pickImage(ImageSource.camera), onGallery: () => _pickImage(ImageSource.gallery))
                  : _ChatView(state: state, scrollCtrl: _scrollCtrl),
            ),
            _InputBar(
              ctrl: _questionCtrl,
              hasImage: state.selectedImage != null,
              isLoading: state.isLoading,
              hasResult: state.result != null,
              onCamera: () => _pickImage(ImageSource.camera),
              onGallery: () => _pickImage(ImageSource.gallery),
              onSend: _analyse,
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final VoidCallback onCamera, onGallery;
  const _EmptyState({required this.onCamera, required this.onGallery});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 90, height: 90,
              decoration: BoxDecoration(color: AppTheme.primary.withOpacity(0.1), shape: BoxShape.circle),
              child: const Icon(Icons.camera_alt_outlined, size: 44, color: AppTheme.primary),
            ),
            const SizedBox(height: 20),
            const Text('Analyse a Nutrition Label', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            const Text('Take a photo or choose from gallery to get started', textAlign: TextAlign.center, style: TextStyle(color: AppTheme.onSurfaceMuted, fontSize: 14)),
            const SizedBox(height: 32),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: onCamera,
                    icon: const Icon(Icons.camera_alt_rounded),
                    label: const Text('Camera'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.primary,
                      side: const BorderSide(color: AppTheme.primary),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: onGallery,
                    icon: const Icon(Icons.photo_library_rounded),
                    label: const Text('Gallery'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatView extends StatelessWidget {
  final AnalyseState state;
  final ScrollController scrollCtrl;
  const _ChatView({required this.state, required this.scrollCtrl});

  @override
  Widget build(BuildContext context) {
    final result = state.result;
    return ListView(
      controller: scrollCtrl,
      padding: const EdgeInsets.symmetric(vertical: 12),
      children: [
        // User's image bubble
        ChatBubble(
          message: 'Please analyse this nutrition label.',
          role: BubbleRole.user,
        ),
        // Show image preview using CrossPlatformImage (web-safe)
        if (state.selectedImage != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: CrossPlatformImage(
                    file: state.selectedImage!.file,
                    bytes: state.selectedImage!.bytes,
                    width: 180,
                    height: 180,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(width: 8),
                const CircleAvatar(radius: 14, backgroundColor: AppTheme.accent, child: Icon(Icons.person_rounded, color: Colors.white, size: 14)),
              ],
            ),
          ),
        if (result != null) ...[
          // AI summary bubble
          ChatBubble(
            message: result.answer.summary,
            role: BubbleRole.assistant,
          ),
          // Nutrition card
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: _NutritionCard(nutrition: result.nutrition),
          ),
          // Recommendations
          if (result.answer.recommendations.isNotEmpty)
            ChatBubble(
              message: '✅ Recommendations:\n${result.answer.recommendations.map((r) => '• $r').join('\n')}',
              role: BubbleRole.assistant,
            ),
          // Warnings
          if (result.answer.warnings.isNotEmpty)
            ChatBubble(
              message: '⚠️ Warnings:\n${result.answer.warnings.map((w) => '• $w').join('\n')}',
              role: BubbleRole.assistant,
            ),
        ],
      ],
    );
  }
}

class _NutritionCard extends StatelessWidget {
  final NutritionData nutrition;
  const _NutritionCard({required this.nutrition});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(left: 36),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Nutrition Facts', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          const Divider(),
          if (nutrition.servingSize != null)
            _Row('Serving Size', nutrition.servingSize!),
          if (nutrition.calories != null)
            _Row('Calories', '${nutrition.calories!.toStringAsFixed(0)} kcal', highlight: true),
          if (nutrition.fatG != null)
            _Row('Total Fat', '${nutrition.fatG!.toStringAsFixed(1)} g'),
          if (nutrition.proteinG != null)
            _Row('Protein', '${nutrition.proteinG!.toStringAsFixed(1)} g'),
          if (nutrition.sugarG != null)
            _Row('Sugar', '${nutrition.sugarG!.toStringAsFixed(1)} g'),
          if (nutrition.sodiumMg != null)
            _Row('Sodium', '${nutrition.sodiumMg!.toStringAsFixed(0)} mg'),
        ],
      ),
    );
  }

  Widget _Row(String label, String value, {bool highlight = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontSize: 13, color: highlight ? AppTheme.onSurface : AppTheme.onSurfaceMuted)),
          Text(value, style: TextStyle(fontSize: 13, fontWeight: highlight ? FontWeight.w700 : FontWeight.w500, color: highlight ? AppTheme.primary : AppTheme.onSurface)),
        ],
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController ctrl;
  final bool hasImage, isLoading, hasResult;
  final VoidCallback onCamera, onGallery, onSend;
  const _InputBar({required this.ctrl, required this.hasImage, required this.isLoading, required this.hasResult, required this.onCamera, required this.onGallery, required this.onSend});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppTheme.divider)),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            IconButton(
              icon: const Icon(Icons.camera_alt_rounded, color: AppTheme.primary),
              onPressed: isLoading ? null : onCamera,
            ),
            IconButton(
              icon: const Icon(Icons.photo_library_rounded, color: AppTheme.primary),
              onPressed: isLoading ? null : onGallery,
            ),
            Expanded(
              child: TextField(
                controller: ctrl,
                decoration: InputDecoration(
                  hintText: hasImage ? 'Ask a question… (optional)' : 'Pick an image first',
                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                  filled: true,
                  fillColor: AppTheme.surfaceVariant,
                  isDense: true,
                ),
                enabled: hasImage && !isLoading,
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: hasImage && !isLoading ? onSend : null,
              style: FilledButton.styleFrom(
                minimumSize: const Size(48, 48),
                padding: EdgeInsets.zero,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              child: const Icon(Icons.send_rounded),
            ),
          ],
        ),
      ),
    );
  }
}
