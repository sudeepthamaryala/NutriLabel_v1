// lib/shared/providers/analyse_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/chat.dart';
import '../services/api_service.dart';
import '../widgets/cross_platform_image.dart';

class AnalyseState {
  final PickedImage? selectedImage;
  final AnalyseResult? result;
  final bool isLoading;
  final String? error;

  const AnalyseState({
    this.selectedImage,
    this.result,
    this.isLoading = false,
    this.error,
  });

  AnalyseState copyWith({
    PickedImage? selectedImage,
    AnalyseResult? result,
    bool? isLoading,
    String? error,
    bool clearImage = false,
    bool clearResult = false,
  }) =>
      AnalyseState(
        selectedImage: clearImage ? null : selectedImage ?? this.selectedImage,
        result: clearResult ? null : result ?? this.result,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

class AnalyseNotifier extends StateNotifier<AnalyseState> {
  AnalyseNotifier() : super(const AnalyseState());

  void setImage(PickedImage image) {
    state = AnalyseState(selectedImage: image);
  }

  void reset() => state = const AnalyseState();

  Future<void> analyse({String? question}) async {
    final image = state.selectedImage;
    if (image == null) return;

    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await ApiService.instance.analyseImage(
        image: image,
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

final analyseProvider =
    StateNotifierProvider<AnalyseNotifier, AnalyseState>((ref) => AnalyseNotifier());
