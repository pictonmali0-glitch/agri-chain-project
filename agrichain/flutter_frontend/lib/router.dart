// lib/router.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'screens/auth/splash_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/auth/forgot_password_screen.dart';
import 'screens/auth/otp_verify_screen.dart';
import 'screens/farmer/farmer_dashboard.dart';
import 'screens/farmer/add_product_screen.dart';
import 'screens/farmer/transfer_screen.dart';
import 'screens/farmer/product_detail_screen.dart';
import 'screens/receiver/receiver_dashboard.dart';
import 'screens/admin/admin_dashboard.dart';
import 'screens/shared/product_tracking_screen.dart';
import 'screens/shared/profile_screen.dart';
import 'services/auth_provider.dart';

GoRouter buildRouter(AuthProvider auth) {
  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final loggedIn = auth.isLoggedIn;
      final publicPaths = {
        '/login', '/register', '/forgot-password', '/',
      };
      final isPublic = publicPaths.contains(state.matchedLocation) ||
          state.matchedLocation.startsWith('/otp-verify');
      if (!loggedIn && !isPublic) return '/login';
      return null;
    },
    routes: [
      // ── Auth ──────────────────────────────────────────────
      GoRoute(path: '/',        builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login',   builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
      GoRoute(path: '/forgot-password', builder: (_, __) => const ForgotPasswordScreen()),
      GoRoute(
        path: '/otp-verify',
        builder: (_, state) {
          final email   = state.uri.queryParameters['email'] ?? '';
          final purpose = state.uri.queryParameters['purpose'] ?? 'verification';
          return OtpVerifyScreen(email: email, purpose: purpose);
        },
      ),

      // ── Farmer ────────────────────────────────────────────
      GoRoute(path: '/farmer', builder: (_, __) => const FarmerDashboard()),
      GoRoute(path: '/farmer/add-product', builder: (_, __) => const AddProductScreen()),
      GoRoute(
        path: '/farmer/product/:id',
        builder: (_, state) => ProductDetailScreen(
            productId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/farmer/transfer/:productId',
        builder: (_, state) => TransferScreen(
            productId: state.pathParameters['productId']!),
      ),

      // ── Receiver ──────────────────────────────────────────
      GoRoute(path: '/receiver', builder: (_, __) => const ReceiverDashboard()),

      // ── Admin ──────────────────────────────────────────────
      GoRoute(path: '/admin', builder: (_, __) => const AdminDashboard()),

      // ── Shared ────────────────────────────────────────────
      GoRoute(
        path: '/product/:id',
        builder: (_, state) => ProductDetailScreen(
            productId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/track/:id',
        builder: (_, state) => ProductTrackingScreen(
            productId: state.pathParameters['id']!),
      ),
      GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
    ],
    errorBuilder: (_, state) => Scaffold(
      backgroundColor: const Color(0xFF0A0F0A),
      body: Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.error_outline_rounded, color: Color(0xFF4CAF50), size: 56),
        const SizedBox(height: 16),
        Text('Page not found',
            style: const TextStyle(color: Colors.white, fontSize: 18,
                fontWeight: FontWeight.w700)),
        const SizedBox(height: 20),
        ElevatedButton(
          onPressed: () => state.namedLocation('/'),
          child: const Text('Go Home'),
        ),
      ])),
    ),
  );
}
