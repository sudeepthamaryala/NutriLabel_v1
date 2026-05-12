// lib/shared/providers/auth_provider.dart
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/user.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

// ── State ─────────────────────────────────────────────────────────────────

class AuthState {
  final UserModel? user;
  final bool isLoading;
  final String? error;
  final bool isAuthenticated;

  const AuthState({
    this.user,
    this.isLoading = false,
    this.error,
    this.isAuthenticated = false,
  });

  AuthState copyWith({
    UserModel? user,
    bool? isLoading,
    String? error,
    bool? isAuthenticated,
  }) =>
      AuthState(
        user: user ?? this.user,
        isLoading: isLoading ?? this.isLoading,
        error: error,
        isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      );
}

// ── Notifier ──────────────────────────────────────────────────────────────

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState()) {
    _init();
  }

  final _supabase = Supabase.instance.client;
  StreamSubscription<dynamic>? _authSubscription;
  bool _authActionInProgress = false;

  Future<void> _init() async {
    // Check if we already have a Supabase session stored
    final session = _supabase.auth.currentSession;
    if (session != null) {
      try {
        final user = await _loadUserFromBackend(session.accessToken);
        if (!mounted || user == null) return;
        state = AuthState(user: user, isAuthenticated: true);
      } catch (_) {
        if (!mounted) return;
        state = const AuthState(isAuthenticated: false);
      }
    }
    if (!mounted) return;

    // Listen to Supabase auth changes
    _authSubscription = _supabase.auth.onAuthStateChange.listen((data) async {
      final session = data.session;
      if (session != null && !_authActionInProgress) {
        await StorageService.saveTokens(
          accessToken: session.accessToken,
          refreshToken: session.refreshToken,
        );
        if (!mounted) return;
        try {
          final user = await _loadUserFromBackend(session.accessToken);
          if (!mounted || user == null) return;
          state = AuthState(user: user, isAuthenticated: true);
        } catch (_) {
          if (!mounted) return;
          state = const AuthState(isAuthenticated: false);
        }
      } else {
        await StorageService.clearAll();
        if (!mounted) return;
        state = const AuthState(isAuthenticated: false);
      }
    });
  }

  Future<UserModel?> _loadUserFromBackend(
    String token, {
    String? fallbackFullName,
  }) async {
    if (!mounted) return null;
    state = state.copyWith(isLoading: true);
    try {
      await StorageService.saveTokens(accessToken: token);
      if (!mounted) return null;
      return await _getOrCreateBackendUser(fallbackFullName: fallbackFullName);
    } catch (e) {
      if (e is ApiException && e.statusCode == 401) {
        rethrow;
      }
      rethrow;
    }
  }

  Future<UserModel> _getOrCreateBackendUser({String? fallbackFullName}) async {
    try {
      return await ApiService.instance.getMe();
    } on ApiException catch (e) {
      if (e.statusCode != 404) rethrow;
      final name = _cleanFallbackName(fallbackFullName);
      return ApiService.instance.register(fullName: name);
    }
  }

  String _cleanFallbackName(String? value) {
    final cleaned = value?.trim();
    if (cleaned != null && cleaned.isNotEmpty) return cleaned;
    final email = _supabase.auth.currentUser?.email;
    final fromEmail = email?.split('@').first.trim();
    if (fromEmail != null && fromEmail.isNotEmpty) return fromEmail;
    return 'Nutrition User';
  }

  // ── Login ────────────────────────────────────────────────────────────────

  Future<void> signIn({
    required String email,
    required String password,
  }) async {
    if (!mounted) return;
    _authActionInProgress = true;
    state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _supabase.auth.signInWithPassword(
        email: email,
        password: password,
      );
      if (!mounted) return;
      final token = res.session!.accessToken;
      await StorageService.saveTokens(
        accessToken: token,
        refreshToken: res.session!.refreshToken,
      );
      if (!mounted) return;
      final user = await _loadUserFromBackend(
        token,
        fallbackFullName: email.split('@').first,
      );
      if (!mounted || user == null) return;
      state = AuthState(user: user, isAuthenticated: true);
    } on AuthException catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: e.message);
    } on ApiException catch (e) {
      if (!mounted) return;
      state = state.copyWith(
        isLoading: false,
        error: e.statusCode == 401
            ? 'Signed in with Supabase, but the backend rejected the token. Check backend Supabase JWT settings.'
            : e.message,
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: e.toString());
    } finally {
      _authActionInProgress = false;
    }
  }

  // ── Sign Up ──────────────────────────────────────────────────────────────

  Future<void> signUp({
    required String email,
    required String password,
    required String fullName,
  }) async {
    if (!mounted) return;
    _authActionInProgress = true;
    state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _supabase.auth.signUp(
        email: email,
        password: password,
      );
      if (!mounted) return;
      final token = res.session?.accessToken;
      if (token == null) {
        // Email confirmation required — Supabase sends a confirmation email
        state = state.copyWith(
          isLoading: false,
          error: 'Check your email to confirm your account.',
        );
        return;
      }
      await StorageService.saveTokens(
        accessToken: token,
        refreshToken: res.session?.refreshToken,
      );
      if (!mounted) return;
      final user = await _loadUserFromBackend(
        token,
        fallbackFullName: fullName,
      );
      if (!mounted || user == null) return;
      state = AuthState(user: user, isAuthenticated: true);
    } on AuthException catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: e.message);
    } on ApiException catch (e) {
      if (!mounted) return;
      state = state.copyWith(
        isLoading: false,
        error: e.statusCode == 401
            ? 'Account was created in Supabase, but the backend rejected the token. Check backend Supabase JWT settings.'
            : e.message,
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: e.toString());
    } finally {
      _authActionInProgress = false;
    }
  }

  // ── Forgot Password ───────────────────────────────────────────────────────

  Future<String?> sendPasswordReset(String email) async {
    if (!mounted) return null;
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _supabase.auth.resetPasswordForEmail(email);
      if (!mounted) return null;
      state = state.copyWith(isLoading: false);
      return null; // null = success
    } on AuthException catch (e) {
      if (!mounted) return e.message;
      state = state.copyWith(isLoading: false, error: e.message);
      return e.message;
    }
  }

  // ── Sign Out ─────────────────────────────────────────────────────────────

  Future<void> signOut() async {
    await _supabase.auth.signOut();
    if (!mounted) return;
    await StorageService.clearAll();
    if (!mounted) return;
    state = const AuthState(isAuthenticated: false);
  }

  void clearError() {
    if (!mounted) return;
    state = state.copyWith(error: null);
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    super.dispose();
  }
}

// ── Providers ─────────────────────────────────────────────────────────────

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);

final isAuthenticatedProvider = Provider<bool>(
  (ref) => ref.watch(authProvider).isAuthenticated,
);
