// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'app/router.dart';
import 'app/theme.dart';
import 'shared/providers/auth_provider.dart';
import 'shared/services/api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Load environment variables from assets/.env
  await dotenv.load(fileName: 'assets/.env');

  // Initialize Supabase
  await Supabase.initialize(
    url: dotenv.env['SUPABASE_URL'] ?? '',
    anonKey: dotenv.env['SUPABASE_ANON_KEY'] ?? '',
  );

  // Initialize API service (sets up Dio with base URL from .env)
  ApiService.instance.init();

  runApp(const ProviderScope(child: NutriLabelApp()));
}

class NutriLabelApp extends ConsumerWidget {
  const NutriLabelApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    // Wire unauthorized callback so 401 responses trigger logout + redirect
    ApiService.instance.onUnauthorized = () {
      ref.read(authProvider.notifier).signOut();
    };

    return MaterialApp.router(
      title: 'NutriLabel AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: router,
    );
  }
}
