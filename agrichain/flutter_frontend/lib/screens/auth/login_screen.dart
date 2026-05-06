// lib/screens/auth/login_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../services/auth_provider.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _pwCtrl    = TextEditingController();
  bool _obscure = true;
  bool _bioAvail = false;

  @override
  void initState() {
    super.initState();
    _checkBio();
  }

  Future<void> _checkBio() async {
    final avail = await context.read<AuthProvider>().isBiometricAvailable();
    setState(() => _bioAvail = avail);
  }

  Future<void> _login() async {
    if (!_form.currentState!.validate()) return;
    final auth = context.read<AuthProvider>();
    final ok = await auth.login(_emailCtrl.text.trim(), _pwCtrl.text);
    if (ok && mounted) _redirect(auth.user!.role);
  }

  Future<void> _bioLogin() async {
    final auth = context.read<AuthProvider>();
    final ok = await auth.biometricLogin();
    if (ok && mounted) _redirect(auth.user!.role);
    else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Biometric login failed. Use password.'),
          backgroundColor: AppColors.error));
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
  void dispose() {
    _emailCtrl.dispose(); _pwCtrl.dispose(); super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Form(
            key: _form,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const SizedBox(height: 40),
              const Center(child: AgriLogo(size: 72)),
              const SizedBox(height: 20),
              const Center(child: Text('AgriChain',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary))),
              const Center(child: Text('Sign in to your account',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 14))),
              const SizedBox(height: 40),

              // Error
              if (auth.error != null)
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.error.withOpacity(0.1),
                    borderRadius: AppRadius.card,
                    border: Border.all(color: AppColors.error.withOpacity(0.3)),
                  ),
                  child: Row(children: [
                    const Icon(Icons.error_outline, color: AppColors.error, size: 18),
                    const SizedBox(width: 8),
                    Expanded(child: Text(auth.error!,
                      style: const TextStyle(color: AppColors.error, fontSize: 13))),
                  ]),
                ),

              AppTextField(
                label: 'Email Address',
                hint: 'farmer@example.com',
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                prefixIcon: const Icon(Icons.email_outlined, color: AppColors.primary),
                validator: (v) => (v == null || !v.contains('@'))
                    ? 'Enter a valid email' : null,
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Password',
                controller: _pwCtrl,
                obscureText: _obscure,
                prefixIcon: const Icon(Icons.lock_outline, color: AppColors.primary),
                suffixIcon: IconButton(
                  icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility,
                      color: AppColors.textSecondary),
                  onPressed: () => setState(() => _obscure = !_obscure),
                ),
                validator: (v) => (v == null || v.length < 6)
                    ? 'Enter your password' : null,
              ),

              // Forgot password
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => context.go('/forgot-password'),
                  child: const Text('Forgot Password?',
                      style: TextStyle(color: AppColors.primary, fontSize: 13)),
                ),
              ),
              const SizedBox(height: AppSpacing.md),

              // Login button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: auth.loading ? null : _login,
                  child: auth.loading
                      ? const SizedBox(width: 20, height: 20,
                          child: CircularProgressIndicator(
                            color: Colors.black, strokeWidth: 2))
                      : const Text('Sign In'),
                ),
              ),

              // Biometric button
              if (_bioAvail) ...[
                const SizedBox(height: AppSpacing.md),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: OutlinedButton.icon(
                    onPressed: _bioLogin,
                    icon: const Icon(Icons.fingerprint_rounded,
                        color: AppColors.primary),
                    label: const Text('Sign In with Fingerprint',
                        style: TextStyle(color: AppColors.primary)),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: AppColors.primary),
                      shape: RoundedRectangleBorder(
                          borderRadius: AppRadius.card),
                    ),
                  ),
                ),
              ],

              const SizedBox(height: AppSpacing.xl),
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Text("Don't have an account? ",
                    style: TextStyle(color: AppColors.textSecondary)),
                GestureDetector(
                  onTap: () => context.go('/register'),
                  child: const Text('Register',
                      style: TextStyle(color: AppColors.primary,
                          fontWeight: FontWeight.w700)),
                ),
              ]),
              const SizedBox(height: AppSpacing.lg),

              // Demo accounts hint
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.surfaceLight,
                  borderRadius: AppRadius.card,
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Demo Accounts',
                      style: TextStyle(color: AppColors.primary,
                          fontSize: 12, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  _demoRow('Admin', 'admin@agrichain.app', 'Admin@123'),
                ]),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _demoRow(String role, String email, String pw) {
    return GestureDetector(
      onTap: () {
        _emailCtrl.text = email;
        _pwCtrl.text = pw;
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Text('$role: $email / $pw',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 11,
                fontFamily: 'monospace')),
      ),
    );
  }
}
