// lib/utils/constants.dart
// AgriChain app-wide constants and theme

import 'package:flutter/material.dart';

// ── API ───────────────────────────────────────────────────────
const String kBaseUrl = 'http://localhost:5000/api';
// For Android emulator, use: 'http://10.0.2.2:5000/api'
// For production: 'https://your-api.agrichain.app/api'

// ── Colors ────────────────────────────────────────────────────
class AppColors {
  static const Color background   = Color(0xFF0A0F0A);
  static const Color surface      = Color(0xFF111A11);
  static const Color surfaceLight = Color(0xFF1A2A1A);
  static const Color primary      = Color(0xFF4CAF50);
  static const Color primaryDark  = Color(0xFF2E7D32);
  static const Color primaryLight = Color(0xFF81C784);
  static const Color accent       = Color(0xFF69F0AE);
  static const Color accentAmber  = Color(0xFFFFB300);
  static const Color error        = Color(0xFFEF5350);
  static const Color warning      = Color(0xFFFF9800);
  static const Color info         = Color(0xFF42A5F5);
  static const Color textPrimary  = Color(0xFFE8F5E9);
  static const Color textSecondary= Color(0xFF9E9E9E);
  static const Color border       = Color(0xFF2A3A2A);
  static const Color borderLight  = Color(0xFF3A5A3A);
  static const Color cardBg       = Color(0xFF121F12);
  static const Color suspicious   = Color(0xFFFF5252);
  static const Color acknowledged = Color(0xFF00E676);
  static const Color inTransit    = Color(0xFF42A5F5);
}

// ── Spacing ───────────────────────────────────────────────────
class AppSpacing {
  static const double xs  = 4.0;
  static const double sm  = 8.0;
  static const double md  = 16.0;
  static const double lg  = 24.0;
  static const double xl  = 32.0;
  static const double xxl = 48.0;
}

// ── Border Radius ─────────────────────────────────────────────
class AppRadius {
  static const double sm = 6.0;
  static const double md = 12.0;
  static const double lg = 20.0;
  static const double xl = 32.0;
  static const BorderRadius card    = BorderRadius.all(Radius.circular(md));
  static const BorderRadius button  = BorderRadius.all(Radius.circular(sm));
  static const BorderRadius dialog  = BorderRadius.all(Radius.circular(lg));
}

// ── Theme ─────────────────────────────────────────────────────
ThemeData buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: AppColors.background,
    colorScheme: const ColorScheme.dark(
      primary: AppColors.primary,
      secondary: AppColors.accent,
      surface: AppColors.surface,
      error: AppColors.error,
      onPrimary: Colors.black,
      onSecondary: Colors.black,
      onSurface: AppColors.textPrimary,
    ),
    fontFamily: 'SpaceGrotesk',
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontFamily: 'SpaceGrotesk',
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
      ),
    ),
    cardTheme: CardTheme(
      color: AppColors.cardBg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: AppRadius.card,
        side: const BorderSide(color: AppColors.border, width: 1),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceLight,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.md,
      ),
      border: OutlineInputBorder(
        borderRadius: AppRadius.card,
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: AppRadius.card,
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: AppRadius.card,
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: AppRadius.card,
        borderSide: const BorderSide(color: AppColors.error),
      ),
      labelStyle: const TextStyle(color: AppColors.textSecondary),
      hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.black,
        shape: RoundedRectangleBorder(borderRadius: AppRadius.card),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.md,
        ),
        textStyle: const TextStyle(
          fontFamily: 'SpaceGrotesk',
          fontWeight: FontWeight.w700,
          fontSize: 15,
        ),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.primary),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.border, thickness: 1),
    chipTheme: ChipThemeData(
      backgroundColor: AppColors.surfaceLight,
      labelStyle: const TextStyle(color: AppColors.textPrimary, fontSize: 12),
      shape: RoundedRectangleBorder(
        borderRadius: AppRadius.card,
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.surface,
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppColors.textSecondary,
      type: BottomNavigationBarType.fixed,
      elevation: 0,
    ),
  );
}

// ── Status helpers ────────────────────────────────────────────
Color statusColor(String status) {
  switch (status.toLowerCase()) {
    case 'acknowledged': return AppColors.acknowledged;
    case 'in_transit':   return AppColors.inTransit;
    case 'delivered':    return AppColors.primaryLight;
    case 'pending':      return AppColors.accentAmber;
    case 'rejected':     return AppColors.error;
    case 'flagged':      return AppColors.suspicious;
    default:             return AppColors.textSecondary;
  }
}

String statusLabel(String status) {
  switch (status.toLowerCase()) {
    case 'acknowledged': return 'Acknowledged';
    case 'in_transit':   return 'In Transit';
    case 'delivered':    return 'Delivered';
    case 'pending':      return 'Pending';
    case 'rejected':     return 'Rejected';
    case 'flagged':      return 'Flagged';
    default:             return status;
  }
}

IconData statusIcon(String status) {
  switch (status.toLowerCase()) {
    case 'acknowledged': return Icons.verified_rounded;
    case 'in_transit':   return Icons.local_shipping_rounded;
    case 'delivered':    return Icons.inventory_2_rounded;
    case 'pending':      return Icons.hourglass_empty_rounded;
    case 'rejected':     return Icons.cancel_rounded;
    case 'flagged':      return Icons.flag_rounded;
    default:             return Icons.help_outline_rounded;
  }
}
