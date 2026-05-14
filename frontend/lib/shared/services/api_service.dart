// lib/shared/services/api_service.dart
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http_parser/http_parser.dart';

import '../models/chat.dart';
import '../models/health_profile.dart';
import '../models/user.dart';
import '../widgets/cross_platform_image.dart';
import 'storage_service.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

/// Singleton Dio client with JWT interceptor.
/// On 401: clears stored token so the router redirects to /login.
class ApiService {
  ApiService._();
  static final ApiService instance = ApiService._();

  late final Dio _dio;
  void Function()? onUnauthorized;

  void init() {
    final baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://10.0.2.2:8000/api/v1';
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Accept': 'application/json'},
      ),
    );

    // ── JWT Interceptor ────────────────────────────────────────────────────
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await StorageService.getAccessToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          final path = error.requestOptions.path;
          final isAuthBootstrapPath =
              path == '/auth/me' || path == '/auth/register';
          if (error.response?.statusCode == 401 && !isAuthBootstrapPath) {
            // Token expired or invalid → clear and redirect to login
            await StorageService.clearAll();
            onUnauthorized?.call();
          }
          handler.next(error);
        },
      ),
    );
  }

  // ── Helper: extract error message ─────────────────────────────────────────
  String _extractError(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) {
      return data['detail'].toString();
    }
    return e.message ?? 'An unexpected error occurred.';
  }

  // ══════════════════════════════════════════════════════════════════════════
  // AUTH
  // ══════════════════════════════════════════════════════════════════════════

  /// Register a local backend user after Supabase login.
  /// Called once after a new Supabase sign-up so the backend creates the row.
  Future<UserModel> register({required String fullName}) async {
    try {
      final res = await _dio.post('/auth/register', data: {'full_name': fullName});
      return UserModel.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException(_extractError(e), statusCode: e.response?.statusCode);
    }
  }

  /// Fetch the currently authenticated user from the backend.
  Future<UserModel> getMe() async {
    try {
      final res = await _dio.get('/auth/me');
      return UserModel.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException(_extractError(e), statusCode: e.response?.statusCode);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PROFILE
  // ══════════════════════════════════════════════════════════════════════════

  Future<HealthProfile> getProfile() async {
    try {
      final res = await _dio.get('/profile');
      return HealthProfile.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  Future<HealthProfile> upsertProfile(HealthProfile profile) async {
    try {
      final res = await _dio.put('/profile', data: profile.toJson());
      return HealthProfile.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ANALYSE
  // ══════════════════════════════════════════════════════════════════════════

  Future<AnalyseResult> analyseImage({
    required PickedImage image,
    String? question,
  }) async {
    try {
      final MultipartFile multipart;
      if (kIsWeb) {
        // Web: use bytes (dart:io File is not available)
        multipart = MultipartFile.fromBytes(
          image.bytes!,
          filename: image.name,
          contentType: MediaType.parse(image.contentType),
        );
      } else {
        // Mobile: use file path
        multipart = await MultipartFile.fromFile(
          image.file!.path,
          filename: image.name,
          contentType: MediaType.parse(image.contentType),
        );
      }
      final formData = FormData.fromMap({
        'image': multipart,
        if (question != null && question.isNotEmpty) 'question': question,
      });
      final res = await _dio.post('/analyse', data: formData);
      return AnalyseResult.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // COMPARE
  // ══════════════════════════════════════════════════════════════════════════

  Future<CompareResult> compareImages({
    required List<PickedImage> images,
    String? question,
  }) async {
    try {
      final fd = FormData();
      for (final img in images) {
        final MultipartFile multipart;
        if (kIsWeb) {
          multipart = MultipartFile.fromBytes(
            img.bytes!,
            filename: img.name,
            contentType: MediaType.parse(img.contentType),
          );
        } else {
          multipart = await MultipartFile.fromFile(
            img.file!.path,
            filename: img.name,
            contentType: MediaType.parse(img.contentType),
          );
        }
        fd.files.add(MapEntry('images', multipart));
      }
      if (question != null && question.isNotEmpty) {
        fd.fields.add(MapEntry('question', question));
      }
      final res = await _dio.post('/compare', data: fd);
      return CompareResult.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // CHAT / HISTORY
  // ══════════════════════════════════════════════════════════════════════════

  Future<List<ChatSession>> getChatSessions() async {
    try {
      final res = await _dio.get('/chat/sessions');
      final list = res.data as List;
      return list
          .map((s) => ChatSession.fromJson(s as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractError(e));
    }
  }
}
