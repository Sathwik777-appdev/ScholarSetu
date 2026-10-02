import 'package:flutter/material.dart';

/// Brand tokens shared with the web console (apps/console/src/index.css).
class AppColors {
  static const ink950 = Color(0xFF070B17);
  static const ink900 = Color(0xFF0C1326);
  static const ink800 = Color(0xFF141D38);
  static const ink700 = Color(0xFF1F2A4D);
  static const saffron = Color(0xFFF59E0B);
  static const saffronLight = Color(0xFFFFB454);
  static const teal = Color(0xFF14B8A6);
  static const tealLight = Color(0xFF2DD4BF);
  static const rose = Color(0xFFE11D48);
  static const surface = Color(0xFFF4F6FB);
  static const card = Colors.white;
  static const line = Color(0xFFE2E8F0);
  static const muted = Color(0xFF64748B);
  static const text = Color(0xFF0F172A);
}

/// Hindi text falls back to the bundled Noto Sans Devanagari (Inter has no Devanagari letters).
const fontFallback = ['NotoSansDevanagari'];

class AppTheme {
  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.ink800,
      primary: AppColors.ink900,
      secondary: AppColors.saffron,
      tertiary: AppColors.teal,
      surface: AppColors.surface,
      error: AppColors.rose,
    );
    final base = ThemeData(useMaterial3: true, colorScheme: scheme, fontFamily: 'Inter', fontFamilyFallback: fontFallback);
    final radius = BorderRadius.circular(16);
    return base.copyWith(
      scaffoldBackgroundColor: AppColors.surface,
      textTheme: base.textTheme.apply(bodyColor: AppColors.text, displayColor: AppColors.text).copyWith(
            headlineMedium: base.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w600, letterSpacing: -0.6),
            headlineSmall: base.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600, letterSpacing: -0.4),
            titleLarge: base.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600, letterSpacing: -0.3),
            titleMedium: base.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.surface,
        foregroundColor: AppColors.text,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(fontFamily: 'Inter', fontFamilyFallback: fontFallback, fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.text),
      ),
      cardTheme: CardThemeData(
        color: AppColors.card,
        elevation: 0,
        margin: const EdgeInsets.symmetric(vertical: 6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: const BorderSide(color: AppColors.line)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(borderRadius: radius, borderSide: const BorderSide(color: AppColors.line)),
        enabledBorder: OutlineInputBorder(borderRadius: radius, borderSide: const BorderSide(color: AppColors.line)),
        focusedBorder: OutlineInputBorder(borderRadius: radius, borderSide: const BorderSide(color: AppColors.saffron, width: 2)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.ink900,
          foregroundColor: Colors.white,
          minimumSize: const Size(0, 52),
          shape: RoundedRectangleBorder(borderRadius: radius),
          textStyle: const TextStyle(fontFamily: 'Inter', fontFamilyFallback: fontFallback, fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(0, 50),
          foregroundColor: AppColors.ink900,
          side: const BorderSide(color: AppColors.line),
          shape: RoundedRectangleBorder(borderRadius: radius),
          textStyle: const TextStyle(fontFamily: 'Inter', fontFamilyFallback: fontFallback, fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: AppColors.saffronLight.withValues(alpha: 0.25),
        height: 68,
        labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(
            fontFamily: 'Inter', fontFamilyFallback: fontFallback, fontSize: 12,
            fontWeight: s.contains(WidgetState.selected) ? FontWeight.w600 : FontWeight.w500,
            color: s.contains(WidgetState.selected) ? AppColors.ink900 : AppColors.muted)),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.ink900,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      dividerTheme: const DividerThemeData(color: AppColors.line, space: 1),
    );
  }
}
