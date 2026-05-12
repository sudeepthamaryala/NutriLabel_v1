// lib/shared/providers/profile_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/health_profile.dart';
import '../services/api_service.dart';

class ProfileState {
  final HealthProfile? profile;
  final bool isLoading;
  final String? error;

  const ProfileState({this.profile, this.isLoading = false, this.error});

  ProfileState copyWith({
    HealthProfile? profile,
    bool? isLoading,
    String? error,
  }) =>
      ProfileState(
        profile: profile ?? this.profile,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

class ProfileNotifier extends StateNotifier<ProfileState> {
  ProfileNotifier() : super(const ProfileState());

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final profile = await ApiService.instance.getProfile();
      state = ProfileState(profile: profile);
    } catch (e) {
      state = ProfileState(error: e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<bool> save(HealthProfile profile) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final saved = await ApiService.instance.upsertProfile(profile);
      state = ProfileState(profile: saved);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceFirst('Exception: ', ''),
      );
      return false;
    }
  }
}

final profileProvider =
    StateNotifierProvider<ProfileNotifier, ProfileState>((ref) => ProfileNotifier());

final hasProfileProvider = Provider<bool>(
  (ref) => ref.watch(profileProvider).profile != null,
);
