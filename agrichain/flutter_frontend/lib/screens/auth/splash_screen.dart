// lib/screens/auth/splash_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../services/auth_provider.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _fade;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(duration: const Duration(milliseconds: 1200), vsync: this);
    _fade  = Tween<double>(begin: 0, end: 1).animate(
        CurvedAnimation(parent: _ctrl, curve: Curves.easeIn));
    _scale = Tween<double>(begin: 0.7, end: 1).animate(
        CurvedAnimation(parent: _ctrl, curve: Curves.easeOutBack));
    _ctrl.forward();
    _init();
  }

  Future<void> _init() async {
    await Future.delayed(const Duration(seconds: 2));
    if (!mounted) return;
    final auth = context.read<AuthProvider>();
    await auth.restoreSession();
    if (!mounted) return;
    if (auth.isLoggedIn) {
      _redirect(auth.user!.role);
    } else {
      context.go('/login');
    }
  }

  void _redirect(String role) {
    switch (role) {
      case 'admin':    context.go('/admin'); break;
      case 'receiver': context.go('/receiver'); break;
      default:         context.go('/farmer'); break;
    }
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: FadeTransition(
          opacity: _fade,
          child: ScaleTransition(
            scale: _scale,
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              const AgriLogo(size: 90),
              const SizedBox(height: 20),
              ShaderMask(
                shaderCallback: (bounds) => const LinearGradient(
                  colors: [AppColors.primary, AppColors.accent],
                ).createShader(bounds),
                child: const Text('AgriChain',
                  style: TextStyle(
                    fontSize: 38, fontWeight: FontWeight.w800,
                    color: Colors.white, letterSpacing: 1.5)),
              ),
              const SizedBox(height: 6),
              const Text('Agricultural Blockchain Supply Chain',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
              const SizedBox(height: 6),
              const Text('Kasese District, Uganda',
                style: TextStyle(color: AppColors.primary, fontSize: 12,
                    fontWeight: FontWeight.w600)),
              const SizedBox(height: 48),
              const SizedBox(
                width: 28, height: 28,
                child: CircularProgressIndicator(
                  color: AppColors.primary, strokeWidth: 2.5),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
