// lib/shared/providers/compare_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/chat.dart';
import '../services/api_service.dart';
import '../widgets/cross_platform_image.dart';

class CompareState {
  final List<PickedImage> images;
  final CompareResult? result;
  final bool isLoading;
  final String? error;

  const CompareState({
    this.images = const [],
    this.result,
    this.isLoading = false,
    this.error,
  });

  CompareState copyWith({
    List<PickedImage>? images,
    CompareResult? result,
    bool? isLoading,
    String? error,
    bool clearResult = false,
  }) =>
      CompareState(
        images: images ?? this.images,
        result: clearResult ? null : result ?? this.result,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

class CompareNotifier extends StateNotifier<CompareState> {
  CompareNotifier() : super(const CompareState());

  void addImage(PickedImage image) {
    if (state.images.length >= 5) return; // max 5 images
    state = state.copyWith(images: [...state.images, image]);
  }

  void removeImage(int index) {
    final updated = [...state.images]..removeAt(index);
    state = state.copyWith(images: updated, clearResult: true);
  }

  void reset() => state = const CompareState();

  Future<void> compare({String? question}) async {
    if (state.images.length < 2) return;

    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await ApiService.instance.compareImages(
        images: state.images,
        question: question,
      );
      state = state.copyWith(result: result, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceFirst('Exception: ', ''),
      );
    }
  }
}

final compareProvider =
    StateNotifierProvider<CompareNotifier, CompareState>((ref) => CompareNotifier());
