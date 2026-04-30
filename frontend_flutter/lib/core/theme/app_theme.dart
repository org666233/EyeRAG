import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

// ── 设计 Token ────────────────────────────────────────────────────────────────
class AppColors {
  AppColors._();

  // 主色：深蓝宝石 (Sapphire)
  static const primary = Color(0xFF1D4ED8);
  static const primaryLight = Color(0xFF3B82F6);
  static const primaryDark = Color(0xFF1E3A8A);

  // 辅助：天蓝 (Sky)
  static const secondary = Color(0xFF0EA5E9);

  // 强调：靛紫 (Indigo)
  static const accent = Color(0xFF6366F1);

  // 中性背景
  static const background = Color(0xFFF0F4FF);
  static const backgroundDark = Color(0xFF090F1E);

  // 表面
  static const surface = Color(0xFFFFFFFF);
  static const surfaceDark = Color(0xFF111827);
  static const surfaceVariantDark = Color(0xFF1C2B40);

  // 文字
  static const textPrimary = Color(0xFF0F172A);
  static const textSecondary = Color(0xFF475569);
  static const textMuted = Color(0xFF94A3B8);

  // 成功/错误
  static const success = Color(0xFF10B981);
  static const error = Color(0xFFEF4444);
  static const warning = Color(0xFFF59E0B);
}

class AppGradients {
  AppGradients._();

  static const hero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1D4ED8), Color(0xFF0EA5E9)],
  );

  static const heroDeep = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFF0F1B35), Color(0xFF1D4ED8)],
  );

  static const cardBlue = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF3B82F6), Color(0xFF6366F1)],
  );

  static const cardCyan = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0EA5E9), Color(0xFF06B6D4)],
  );

  static const cardGreen = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF10B981), Color(0xFF059669)],
  );

  static const cardAmber = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFF59E0B), Color(0xFFEF4444)],
  );

  // 对话头像渐变（按索引轮换）
  static const List<LinearGradient> avatarPalette = [
    cardBlue,
    cardCyan,
    cardGreen,
    LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [Color(0xFF8B5CF6), Color(0xFFEC4899)],
    ),
    LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [Color(0xFF06B6D4), Color(0xFF3B82F6)],
    ),
  ];
}

// ── 主题 ──────────────────────────────────────────────────────────────────────
class AppTheme {
  AppTheme._();

  static ThemeData get light {
    const primary = AppColors.primary;
    final colorScheme = ColorScheme(
      brightness: Brightness.light,
      primary: primary,
      onPrimary: Colors.white,
      primaryContainer: const Color(0xFFDBEAFE),
      onPrimaryContainer: AppColors.primaryDark,
      secondary: AppColors.secondary,
      onSecondary: Colors.white,
      secondaryContainer: const Color(0xFFE0F2FE),
      onSecondaryContainer: const Color(0xFF0C4A6E),
      tertiary: AppColors.accent,
      onTertiary: Colors.white,
      tertiaryContainer: const Color(0xFFE0E7FF),
      onTertiaryContainer: const Color(0xFF312E81),
      error: AppColors.error,
      onError: Colors.white,
      errorContainer: const Color(0xFFFEE2E2),
      onErrorContainer: const Color(0xFF7F1D1D),
      surface: AppColors.surface,
      onSurface: AppColors.textPrimary,
      surfaceContainerLowest: const Color(0xFFF8FAFF),
      surfaceContainerLow: const Color(0xFFF0F4FF),
      surfaceContainer: const Color(0xFFE8EEFF),
      surfaceContainerHigh: const Color(0xFFDDE5FF),
      surfaceContainerHighest: const Color(0xFFD0DCFF),
      onSurfaceVariant: AppColors.textSecondary,
      outline: const Color(0xFFCBD5E1),
      outlineVariant: const Color(0xFFE2E8F0),
      shadow: const Color(0x1A1D4ED8),
      scrim: const Color(0x801D4ED8),
      inverseSurface: AppColors.textPrimary,
      onInverseSurface: Colors.white,
      inversePrimary: const Color(0xFF93C5FD),
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.background,
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        systemOverlayStyle: SystemUiOverlayStyle.dark,
        titleTextStyle: const TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          color: AppColors.textPrimary,
          letterSpacing: -0.3,
        ),
        iconTheme:
            const IconThemeData(color: AppColors.textSecondary, size: 22),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: Colors.white,
        shadowColor: const Color(0x141D4ED8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: Color(0xFFE8EEFF), width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide:
              const BorderSide(color: AppColors.error),
        ),
        labelStyle:
            const TextStyle(color: AppColors.textSecondary, fontSize: 15),
        hintStyle:
            const TextStyle(color: AppColors.textMuted, fontSize: 15),
        prefixIconColor: AppColors.textMuted,
        suffixIconColor: AppColors.textMuted,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          minimumSize:
              WidgetStateProperty.all(const Size(double.infinity, 52)),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14)),
          ),
          elevation: WidgetStateProperty.all(0),
          textStyle: WidgetStateProperty.all(
            const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.2),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        elevation: 0,
        backgroundColor: Colors.transparent,
        indicatorColor: Colors.transparent,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 11,
            fontWeight:
                selected ? FontWeight.w600 : FontWeight.w400,
            color: selected ? primary : AppColors.textMuted,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? primary : AppColors.textMuted,
            size: 24,
          );
        }),
      ),
      listTileTheme: const ListTileThemeData(
        contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 4),
        minLeadingWidth: 0,
      ),
      dividerTheme: const DividerThemeData(
        color: Color(0xFFEEF2FF),
        thickness: 1,
        space: 0,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: const Color(0xFFEEF2FF),
        selectedColor: const Color(0xFFDBEAFE),
        labelStyle:
            const TextStyle(fontSize: 13, color: AppColors.textSecondary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(
            fontSize: 48,
            fontWeight: FontWeight.w800,
            letterSpacing: -1.5,
            color: AppColors.textPrimary),
        headlineLarge: TextStyle(
            fontSize: 32,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.8,
            color: AppColors.textPrimary),
        headlineMedium: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.5,
            color: AppColors.textPrimary),
        headlineSmall: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.3,
            color: AppColors.textPrimary),
        titleLarge: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.2,
            color: AppColors.textPrimary),
        titleMedium: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w500,
            color: AppColors.textPrimary),
        titleSmall: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary),
        bodyLarge: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w400,
            height: 1.6,
            color: AppColors.textPrimary),
        bodyMedium: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w400,
            height: 1.5,
            color: AppColors.textPrimary),
        bodySmall: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w400,
            color: AppColors.textSecondary),
        labelLarge: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.3,
            color: AppColors.textPrimary),
        labelMedium: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            letterSpacing: 0.4,
            color: AppColors.textSecondary),
        labelSmall: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            letterSpacing: 0.5,
            color: AppColors.textMuted),
      ),
    );
  }

  static ThemeData get dark {
    const primary = Color(0xFF60A5FA);
    final colorScheme = ColorScheme(
      brightness: Brightness.dark,
      primary: primary,
      onPrimary: const Color(0xFF1E3A8A),
      primaryContainer: const Color(0xFF1D3461),
      onPrimaryContainer: const Color(0xFFBFDBFE),
      secondary: const Color(0xFF38BDF8),
      onSecondary: const Color(0xFF0C4A6E),
      secondaryContainer: const Color(0xFF0C3B5E),
      onSecondaryContainer: const Color(0xFFBAE6FD),
      tertiary: const Color(0xFFA5B4FC),
      onTertiary: const Color(0xFF312E81),
      tertiaryContainer: const Color(0xFF312E81),
      onTertiaryContainer: const Color(0xFFE0E7FF),
      error: const Color(0xFFFCA5A5),
      onError: const Color(0xFF7F1D1D),
      errorContainer: const Color(0xFF7F1D1D),
      onErrorContainer: const Color(0xFFFEE2E2),
      surface: AppColors.surfaceDark,
      onSurface: const Color(0xFFF1F5F9),
      surfaceContainerLowest: AppColors.backgroundDark,
      surfaceContainerLow: const Color(0xFF111827),
      surfaceContainer: const Color(0xFF1C2B40),
      surfaceContainerHigh: const Color(0xFF243348),
      surfaceContainerHighest: const Color(0xFF2D3D52),
      onSurfaceVariant: const Color(0xFF94A3B8),
      outline: const Color(0xFF334155),
      outlineVariant: const Color(0xFF1E293B),
      shadow: Colors.black54,
      scrim: Colors.black87,
      inverseSurface: const Color(0xFFF1F5F9),
      onInverseSurface: AppColors.textPrimary,
      inversePrimary: AppColors.primary,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.backgroundDark,
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: const Color(0xFFF1F5F9),
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        systemOverlayStyle: SystemUiOverlayStyle.light,
        titleTextStyle: const TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          color: Color(0xFFF1F5F9),
          letterSpacing: -0.3,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: AppColors.surfaceDark,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: Color(0xFF1E293B), width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceVariantDark,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF334155)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF334155)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 15),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          minimumSize:
              WidgetStateProperty.all(const Size(double.infinity, 52)),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14)),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        elevation: 0,
        backgroundColor: Colors.transparent,
        indicatorColor: Colors.transparent,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 11,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            color: selected ? primary : const Color(0xFF64748B),
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? primary : const Color(0xFF64748B),
            size: 24,
          );
        }),
      ),
    );
  }
}
