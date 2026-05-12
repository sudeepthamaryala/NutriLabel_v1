// lib/app/theme.dart
import 'package:flutter/material.dart';

class AppTheme {
  // Brand colors
  static const Color primary = Color(0xFF0D7377);
  static const Color primaryDark = Color(0xFF0A5C60);
  static const Color primaryLight = Color(0xFF14A8AE);
  static const Color accent = Color(0xFFE8A838);
  static const Color accentDark = Color(0xFFCA8F20);

  // Neutral palette
  static const Color surface = Color(0xFFF8FAFB);
  static const Color surfaceVariant = Color(0xFFEDF2F4);
  static const Color onSurface = Color(0xFF1A2327);
  static const Color onSurfaceMuted = Color(0xFF6B7B82);
  static const Color divider = Color(0xFFE0E8EA);

  // Semantic
  static const Color success = Color(0xFF2E9E6B);
  static const Color warning = Color(0xFFE8A838);
  static const Color error = Color(0xFFD94F4F);

  static ThemeData get light {
    const colorScheme = ColorScheme(
      brightness: Brightness.light,
      primary: primary,
      onPrimary: Colors.white,
      primaryContainer: Color(0xFFB2E4E6),
      onPrimaryContainer: Color(0xFF002021),
      secondary: accent,
      onSecondary: Colors.white,
      secondaryContainer: Color(0xFFFFDEA4),
      onSecondaryContainer: Color(0xFF271900),
      tertiary: Color(0xFF4A6572),
      onTertiary: Colors.white,
      error: error,
      onError: Colors.white,
      background: surface,
      onBackground: onSurface,
      surface: Colors.white,
      onSurface: onSurface,
      outline: divider,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      fontFamily: 'Inter',

      // AppBar
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: onSurface,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: true,
        titleTextStyle: TextStyle(
          fontFamily: 'Inter',
          fontSize: 17,
          fontWeight: FontWeight.w600,
          color: onSurface,
        ),
      ),

      // Scaffold
      scaffoldBackgroundColor: surface,

      // Card
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: divider),
        ),
        margin: EdgeInsets.zero,
      ),

      // Input fields
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: divider),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: error),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        hintStyle: const TextStyle(color: onSurfaceMuted, fontSize: 15),
        labelStyle: const TextStyle(color: onSurfaceMuted, fontSize: 15),
      ),

      // Filled button (primary CTA)
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          minimumSize: const Size(double.infinity, 52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      // Text button
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      // Bottom nav
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: primary.withOpacity(0.12),
        iconTheme: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return const IconThemeData(color: primary);
          }
          return const IconThemeData(color: onSurfaceMuted);
        }),
        labelTextStyle: MaterialStateProperty.resolveWith((states) {
          if (states.contains(MaterialState.selected)) {
            return const TextStyle(
              fontFamily: 'Inter',
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: primary,
            );
          }
          return const TextStyle(
            fontFamily: 'Inter',
            fontSize: 12,
            color: onSurfaceMuted,
          );
        }),
        elevation: 8,
        shadowColor: Colors.black26,
      ),

      // Chip
      chipTheme: ChipThemeData(
        backgroundColor: surfaceVariant,
        selectedColor: primary.withOpacity(0.15),
        labelStyle: const TextStyle(fontSize: 13, fontFamily: 'Inter'),
        side: const BorderSide(color: divider),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),

      // SnackBar
      snackBarTheme: SnackBarThemeData(
        backgroundColor: onSurface,
        contentTextStyle: const TextStyle(color: Colors.white, fontFamily: 'Inter'),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        behavior: SnackBarBehavior.floating,
      ),

      // Divider
      dividerTheme: const DividerThemeData(color: divider, thickness: 1),

      // Text
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.w700, color: onSurface),
        displayMedium: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: onSurface),
        headlineLarge: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: onSurface),
        headlineMedium: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: onSurface),
        headlineSmall: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: onSurface),
        titleLarge: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: onSurface),
        titleMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: onSurface),
        bodyLarge: TextStyle(fontSize: 15, fontWeight: FontWeight.w400, color: onSurface),
        bodyMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w400, color: onSurface),
        bodySmall: TextStyle(fontSize: 12, fontWeight: FontWeight.w400, color: onSurfaceMuted),
        labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: onSurface),
      ),
    );
  }
}
