// lib/screens/auth/register_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:pin_code_fields/pin_code_fields.dart';
import '../../services/auth_provider.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _nameCtrl     = TextEditingController();
  final _emailCtrl    = TextEditingController();
  final _phoneCtrl    = TextEditingController();
  final _locationCtrl = TextEditingController();
  final _pwCtrl       = TextEditingController();
  final _pw2Ctrl      = TextEditingController();

  String _role = 'farmer';
  bool _obscure = true;
  bool _loading = false;
  bool _otpSent = false;
  bool _emailVerified = false;
  String _otpCode = '';
  String? _error;

  Future<void> _sendOtp() async {
    final email = _emailCtrl.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = 'Enter a valid email first.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final res = await ApiService.requestOtp(email, 'registration');
    setState(() => _loading = false);
    if (res.success) {
      setState(() => _otpSent = true);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✅ OTP sent to your email!'),
            backgroundColor: AppColors.primary));
      }
    } else {
      setState(() => _error = res.errorMessage);
    }
  }

  Future<void> _verifyOtp() async {
    if (_otpCode.length != 6) return;
    setState(() { _loading = true; _error = null; });
    final res = await ApiService.verifyOtp(_emailCtrl.text.trim(), _otpCode, 'registration');
    setState(() => _loading = false);
    if (res.success) {
      setState(() => _emailVerified = true);
    } else {
      setState(() => _error = res.errorMessage);
    }
  }

  Future<void> _register() async {
    if (!_form.currentState!.validate()) return;
    if (!_emailVerified) {
      setState(() => _error = 'Please verify your email first.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final auth = context.read<AuthProvider>();
    final ok = await auth.register({
      'name': _nameCtrl.text.trim(),
      'email': _emailCtrl.text.trim(),
      'phone': _phoneCtrl.text.trim(),
      'location': _locationCtrl.text.trim(),
      'password': _pwCtrl.text,
      'role': _role,
      'otp_code': _otpCode,
    });
    setState(() => _loading = false);
    if (ok && mounted) {
      switch (auth.user!.role) {
        case 'admin':    context.go('/admin'); break;
        case 'receiver': context.go('/receiver'); break;
        default:         context.go('/farmer'); break;
      }
    } else if (mounted) {
      setState(() => _error = auth.error);
    }
  }

  @override
  void dispose() {
    for (final c in [_nameCtrl, _emailCtrl, _phoneCtrl, _locationCtrl, _pwCtrl, _pw2Ctrl]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Create Account'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/login'),
        ),
      ),
      body: LoadingOverlay(
        isLoading: _loading,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Form(
            key: _form,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              // Error
              if (_error != null)
                Container(
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.error.withOpacity(0.1),
                    borderRadius: AppRadius.card,
                    border: Border.all(color: AppColors.error.withOpacity(0.3)),
                  ),
                  child: Text(_error!, style: const TextStyle(color: AppColors.error)),
                ),

              AppTextField(
                label: 'Full Name',
                controller: _nameCtrl,
                prefixIcon: const Icon(Icons.person_outline, color: AppColors.primary),
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Name required' : null,
              ),
              const SizedBox(height: AppSpacing.md),

              // Email + OTP send
              Row(children: [
                Expanded(
                  child: AppTextField(
                    label: 'Email Address',
                    controller: _emailCtrl,
                    keyboardType: TextInputType.emailAddress,
                    prefixIcon: const Icon(Icons.email_outlined, color: AppColors.primary),
                    suffixIcon: _emailVerified
                        ? const Icon(Icons.verified_rounded, color: AppColors.accent)
                        : null,
                    validator: (v) => (v == null || !v.contains('@')) ? 'Valid email required' : null,
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _emailVerified ? null : _sendOtp,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                    backgroundColor: _emailVerified ? AppColors.border : AppColors.primary,
                  ),
                  child: Text(_emailVerified ? '✓' : 'Send OTP',
                      style: const TextStyle(fontSize: 12)),
                ),
              ]),

              // OTP input
              if (_otpSent && !_emailVerified) ...[
                const SizedBox(height: AppSpacing.md),
                const Text('Enter 6-digit code sent to your email:',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                const SizedBox(height: 8),
                PinCodeTextField(
                  appContext: context,
                  length: 6,
                  keyboardType: TextInputType.number,
                  animationType: AnimationType.fade,
                  pinTheme: PinTheme(
                    shape: PinCodeFieldShape.box,
                    borderRadius: BorderRadius.circular(8),
                    fieldHeight: 50,
                    fieldWidth: 44,
                    activeFillColor: AppColors.surfaceLight,
                    inactiveFillColor: AppColors.cardBg,
                    selectedFillColor: AppColors.surfaceLight,
                    activeColor: AppColors.primary,
                    inactiveColor: AppColors.border,
                    selectedColor: AppColors.accent,
                  ),
                  enableActiveFill: true,
                  onCompleted: (v) { setState(() => _otpCode = v); _verifyOtp(); },
                  onChanged: (v) => setState(() => _otpCode = v),
                ),
              ],

              if (_emailVerified)
                Container(
                  padding: const EdgeInsets.all(10),
                  margin: const EdgeInsets.only(top: AppSpacing.sm),
                  decoration: BoxDecoration(
                    color: AppColors.accent.withOpacity(0.1),
                    borderRadius: AppRadius.card,
                    border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                  ),
                  child: const Row(children: [
                    Icon(Icons.verified_rounded, color: AppColors.accent, size: 16),
                    SizedBox(width: 8),
                    Text('Email verified ✓',
                        style: TextStyle(color: AppColors.accent, fontSize: 13)),
                  ]),
                ),

              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Phone Number',
                controller: _phoneCtrl,
                keyboardType: TextInputType.phone,
                prefixIcon: const Icon(Icons.phone_outlined, color: AppColors.primary),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Location / District',
                hint: 'e.g. Kasese District, Uganda',
                controller: _locationCtrl,
                prefixIcon: const Icon(Icons.location_on_outlined, color: AppColors.primary),
              ),
              const SizedBox(height: AppSpacing.md),

              // Role selector
              const Text('Role', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
              const SizedBox(height: 8),
              Row(children: [
                _roleBtn('farmer', 'Farmer', Icons.agriculture_rounded),
                const SizedBox(width: 8),
                _roleBtn('receiver', 'Receiver', Icons.inventory_2_rounded),
              ]),
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
                validator: (v) {
                  if (v == null || v.length < 8) return 'Min 8 characters';
                  if (!v.contains(RegExp(r'[A-Z]'))) return 'Include uppercase letter';
                  if (!v.contains(RegExp(r'[0-9]'))) return 'Include a number';
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Confirm Password',
                controller: _pw2Ctrl,
                obscureText: true,
                prefixIcon: const Icon(Icons.lock_outline, color: AppColors.primary),
                validator: (v) => v != _pwCtrl.text ? 'Passwords do not match' : null,
              ),
              const SizedBox(height: AppSpacing.xl),

              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _loading ? null : _register,
                  child: const Text('Create Account'),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Center(
                child: GestureDetector(
                  onTap: () => context.go('/login'),
                  child: const Text.rich(TextSpan(children: [
                    TextSpan(text: 'Already have an account? ',
                        style: TextStyle(color: AppColors.textSecondary)),
                    TextSpan(text: 'Sign In',
                        style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
                  ])),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _roleBtn(String value, String label, IconData icon) {
    final selected = _role == value;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _role = value),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            color: selected ? AppColors.primary.withOpacity(0.15) : AppColors.cardBg,
            borderRadius: AppRadius.card,
            border: Border.all(
              color: selected ? AppColors.primary : AppColors.border,
              width: selected ? 2 : 1,
            ),
          ),
          child: Column(children: [
            Icon(icon, color: selected ? AppColors.primary : AppColors.textSecondary),
            const SizedBox(height: 4),
            Text(label, style: TextStyle(
              color: selected ? AppColors.primary : AppColors.textSecondary,
              fontWeight: selected ? FontWeight.w700 : FontWeight.normal,
              fontSize: 13,
            )),
          ]),
        ),
      ),
    );
  }
}
