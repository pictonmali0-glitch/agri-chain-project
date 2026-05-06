// lib/screens/auth/forgot_password_screen.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:pin_code_fields/pin_code_fields.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});
  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  // Step 0 = enter email, Step 1 = enter OTP, Step 2 = new password, Step 3 = done
  int _step = 0;

  final _emailCtrl  = TextEditingController();
  final _pw1Ctrl    = TextEditingController();
  final _pw2Ctrl    = TextEditingController();
  String _otpCode   = '';
  bool _loading     = false;
  bool _obscure     = true;
  String? _error;

  // ── Step 0: send OTP ────────────────────────────────────────
  Future<void> _sendOtp() async {
    final email = _emailCtrl.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = 'Enter a valid email address.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final res = await ApiService.requestOtp(email, 'reset');
    setState(() => _loading = false);
    if (res.success) {
      setState(() => _step = 1);
    } else {
      setState(() => _error = res.errorMessage);
    }
  }

  // ── Step 1: verify OTP ──────────────────────────────────────
  Future<void> _verifyOtp() async {
    if (_otpCode.length != 6) return;
    setState(() { _loading = true; _error = null; });
    final res = await ApiService.verifyOtp(_emailCtrl.text.trim(), _otpCode, 'reset');
    setState(() => _loading = false);
    if (res.success) {
      setState(() => _step = 2);
    } else {
      setState(() => _error = res.errorMessage);
    }
  }

  // ── Step 2: reset password ──────────────────────────────────
  Future<void> _resetPassword() async {
    final pw  = _pw1Ctrl.text;
    final pw2 = _pw2Ctrl.text;
    if (pw.length < 8) {
      setState(() => _error = 'Password must be at least 8 characters.');
      return;
    }
    if (!pw.contains(RegExp(r'[A-Z]'))) {
      setState(() => _error = 'Include at least one uppercase letter.');
      return;
    }
    if (!pw.contains(RegExp(r'[0-9]'))) {
      setState(() => _error = 'Include at least one digit.');
      return;
    }
    if (pw != pw2) {
      setState(() => _error = 'Passwords do not match.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final res = await ApiService.resetPassword(_emailCtrl.text.trim(), _otpCode, pw);
    setState(() => _loading = false);
    if (res.success) {
      setState(() => _step = 3);
    } else {
      setState(() => _error = res.errorMessage);
    }
  }

  @override
  void dispose() {
    _emailCtrl.dispose(); _pw1Ctrl.dispose(); _pw2Ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Reset Password'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/login'),
        ),
      ),
      body: LoadingOverlay(
        isLoading: _loading,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // Progress indicator
            _buildProgress(),
            const SizedBox(height: AppSpacing.xl),

            // Error banner
            if (_error != null)
              Container(
                margin: const EdgeInsets.only(bottom: AppSpacing.md),
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.error.withOpacity(0.1),
                  borderRadius: AppRadius.card,
                  border: Border.all(color: AppColors.error.withOpacity(0.3)),
                ),
                child: Row(children: [
                  const Icon(Icons.error_outline, color: AppColors.error, size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_error!,
                      style: const TextStyle(color: AppColors.error, fontSize: 13))),
                ]),
              ),

            // Step content
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: _buildStep(),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _buildProgress() {
    final steps = ['Email', 'Verify OTP', 'New Password', 'Done'];
    return Row(
      children: List.generate(steps.length, (i) {
        final active   = i == _step;
        final complete = i < _step;
        return Expanded(
          child: Row(children: [
            Column(children: [
              Container(
                width: 28, height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: complete
                      ? AppColors.primary
                      : active
                          ? AppColors.primary.withOpacity(0.2)
                          : AppColors.surfaceLight,
                  border: Border.all(
                    color: (active || complete) ? AppColors.primary : AppColors.border,
                    width: active ? 2 : 1,
                  ),
                ),
                child: Center(child: complete
                    ? const Icon(Icons.check_rounded, color: Colors.black, size: 14)
                    : Text('${i + 1}',
                        style: TextStyle(
                          color: active ? AppColors.primary : AppColors.textSecondary,
                          fontSize: 12, fontWeight: FontWeight.w700))),
              ),
              const SizedBox(height: 4),
              Text(steps[i],
                  style: TextStyle(
                    color: active ? AppColors.primary : AppColors.textSecondary,
                    fontSize: 10, fontWeight: active ? FontWeight.w700 : FontWeight.normal)),
            ]),
            if (i < steps.length - 1)
              Expanded(child: Container(
                height: 1,
                margin: const EdgeInsets.only(bottom: 20),
                color: i < _step ? AppColors.primary : AppColors.border,
              )),
          ]),
        );
      }),
    );
  }

  Widget _buildStep() {
    switch (_step) {
      case 0: return _stepEmail();
      case 1: return _stepOtp();
      case 2: return _stepNewPassword();
      case 3: return _stepDone();
      default: return const SizedBox.shrink();
    }
  }

  // Step 0 ──────────────────────────────────────────────────
  Widget _stepEmail() {
    return Column(key: const ValueKey(0), crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Forgot your password?',
          style: TextStyle(color: AppColors.textPrimary, fontSize: 22,
              fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      const Text('Enter your registered email and we\'ll send a 6-digit reset code.',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
      const SizedBox(height: AppSpacing.xl),
      AppTextField(
        label: 'Email Address',
        hint: 'your@email.com',
        controller: _emailCtrl,
        keyboardType: TextInputType.emailAddress,
        prefixIcon: const Icon(Icons.email_outlined, color: AppColors.primary),
      ),
      const SizedBox(height: AppSpacing.xl),
      SizedBox(
        width: double.infinity, height: 52,
        child: ElevatedButton.icon(
          onPressed: _sendOtp,
          icon: const Icon(Icons.send_rounded),
          label: const Text('Send Reset Code'),
        ),
      ),
    ]);
  }

  // Step 1 ──────────────────────────────────────────────────
  Widget _stepOtp() {
    return Column(key: const ValueKey(1), crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Check your email',
          style: TextStyle(color: AppColors.textPrimary, fontSize: 22,
              fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      Text('We sent a 6-digit code to ${_emailCtrl.text}',
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 14)),
      const SizedBox(height: AppSpacing.xl),
      PinCodeTextField(
        appContext: context,
        length: 6,
        keyboardType: TextInputType.number,
        animationType: AnimationType.fade,
        pinTheme: PinTheme(
          shape: PinCodeFieldShape.box,
          borderRadius: BorderRadius.circular(8),
          fieldHeight: 52,
          fieldWidth: 46,
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
      const SizedBox(height: AppSpacing.md),
      Center(child: TextButton(
        onPressed: _sendOtp,
        child: const Text('Resend Code', style: TextStyle(color: AppColors.primary)),
      )),
      const SizedBox(height: AppSpacing.md),
      Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.surfaceLight, borderRadius: AppRadius.card,
          border: Border.all(color: AppColors.border)),
        child: const Row(children: [
          Icon(Icons.info_outline_rounded, color: AppColors.textSecondary, size: 16),
          SizedBox(width: 8),
          Expanded(child: Text('Code expires in 5 minutes. Check spam folder if not received.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12))),
        ]),
      ),
    ]);
  }

  // Step 2 ──────────────────────────────────────────────────
  Widget _stepNewPassword() {
    return Column(key: const ValueKey(2), crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Set new password',
          style: TextStyle(color: AppColors.textPrimary, fontSize: 22,
              fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      const Text('Choose a strong password for your account.',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
      const SizedBox(height: AppSpacing.xl),

      AppTextField(
        label: 'New Password',
        controller: _pw1Ctrl,
        obscureText: _obscure,
        prefixIcon: const Icon(Icons.lock_outline, color: AppColors.primary),
        suffixIcon: IconButton(
          icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility,
              color: AppColors.textSecondary),
          onPressed: () => setState(() => _obscure = !_obscure),
        ),
      ),
      const SizedBox(height: AppSpacing.md),
      AppTextField(
        label: 'Confirm New Password',
        controller: _pw2Ctrl,
        obscureText: true,
        prefixIcon: const Icon(Icons.lock_outline, color: AppColors.primary),
      ),
      const SizedBox(height: AppSpacing.sm),

      // Password requirements hint
      _pwRule('At least 8 characters', _pw1Ctrl.text.length >= 8),
      _pwRule('Contains uppercase letter', _pw1Ctrl.text.contains(RegExp(r'[A-Z]'))),
      _pwRule('Contains a number', _pw1Ctrl.text.contains(RegExp(r'[0-9]'))),

      const SizedBox(height: AppSpacing.xl),
      SizedBox(
        width: double.infinity, height: 52,
        child: ElevatedButton.icon(
          onPressed: _resetPassword,
          icon: const Icon(Icons.lock_reset_rounded),
          label: const Text('Reset Password'),
        ),
      ),
    ]);
  }

  Widget _pwRule(String label, bool met) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(children: [
        Icon(met ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
            color: met ? AppColors.primary : AppColors.textSecondary, size: 14),
        const SizedBox(width: 6),
        Text(label, style: TextStyle(
            color: met ? AppColors.primary : AppColors.textSecondary, fontSize: 12)),
      ]),
    );
  }

  // Step 3 ──────────────────────────────────────────────────
  Widget _stepDone() {
    return Center(
      key: const ValueKey(3),
      child: Column(children: [
        const SizedBox(height: AppSpacing.xl),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.check_circle_rounded,
              color: AppColors.primary, size: 72),
        ),
        const SizedBox(height: AppSpacing.lg),
        const Text('Password Reset!',
            style: TextStyle(color: AppColors.textPrimary, fontSize: 24,
                fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        const Text('Your password has been updated successfully.\nYou can now sign in.',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
            textAlign: TextAlign.center),
        const SizedBox(height: AppSpacing.xl),
        SizedBox(
          width: double.infinity, height: 52,
          child: ElevatedButton(
            onPressed: () => context.go('/login'),
            child: const Text('Back to Sign In'),
          ),
        ),
      ]),
    );
  }
}
