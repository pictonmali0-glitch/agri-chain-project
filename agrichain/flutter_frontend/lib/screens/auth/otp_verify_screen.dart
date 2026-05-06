// lib/screens/auth/otp_verify_screen.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:pin_code_fields/pin_code_fields.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

/// Generic OTP verification screen.
/// Receives [email] and [purpose] via query parameters.
class OtpVerifyScreen extends StatefulWidget {
  final String email;
  final String purpose;
  const OtpVerifyScreen({super.key, required this.email, required this.purpose});

  @override
  State<OtpVerifyScreen> createState() => _OtpVerifyScreenState();
}

class _OtpVerifyScreenState extends State<OtpVerifyScreen> {
  String _code = '';
  bool _loading = false;
  String? _error;
  int _resendCountdown = 0;

  @override
  void initState() {
    super.initState();
    _startResendTimer();
  }

  void _startResendTimer() {
    setState(() => _resendCountdown = 60);
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (!mounted) return false;
      setState(() => _resendCountdown--);
      return _resendCountdown > 0;
    });
  }

  Future<void> _verify() async {
    if (_code.length != 6) return;
    setState(() { _loading = true; _error = null; });
    final res = await ApiService.verifyOtp(widget.email, _code, widget.purpose);
    setState(() => _loading = false);
    if (res.success && mounted) {
      context.pop(true); // return success to caller
    } else {
      setState(() => _error = res.errorMessage);
    }
  }

  Future<void> _resend() async {
    if (_resendCountdown > 0) return;
    setState(() { _loading = true; _error = null; });
    final res = await ApiService.requestOtp(widget.email, widget.purpose);
    setState(() => _loading = false);
    if (res.success) {
      _startResendTimer();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('New code sent!'),
              backgroundColor: AppColors.primary));
      }
    } else {
      setState(() => _error = res.errorMessage);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Verify Email')),
      body: LoadingOverlay(
        isLoading: _loading,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const SizedBox(height: AppSpacing.md),
            const Icon(Icons.mark_email_read_rounded,
                color: AppColors.primary, size: 56),
            const SizedBox(height: AppSpacing.md),
            const Text('Enter verification code',
                style: TextStyle(color: AppColors.textPrimary, fontSize: 22,
                    fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            RichText(text: TextSpan(children: [
              const TextSpan(text: 'We sent a 6-digit code to ',
                  style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
              TextSpan(text: widget.email,
                  style: const TextStyle(color: AppColors.primary,
                      fontWeight: FontWeight.w600, fontSize: 14)),
            ])),
            const SizedBox(height: AppSpacing.xl),

            if (_error != null)
              Container(
                margin: const EdgeInsets.only(bottom: AppSpacing.md),
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.error.withOpacity(0.1),
                  borderRadius: AppRadius.card,
                  border: Border.all(color: AppColors.error.withOpacity(0.3))),
                child: Text(_error!, style: const TextStyle(color: AppColors.error)),
              ),

            PinCodeTextField(
              appContext: context,
              length: 6,
              keyboardType: TextInputType.number,
              animationType: AnimationType.scale,
              pinTheme: PinTheme(
                shape: PinCodeFieldShape.box,
                borderRadius: BorderRadius.circular(10),
                fieldHeight: 56,
                fieldWidth: 48,
                activeFillColor: AppColors.surfaceLight,
                inactiveFillColor: AppColors.cardBg,
                selectedFillColor: AppColors.surfaceLight,
                activeColor: AppColors.primary,
                inactiveColor: AppColors.border,
                selectedColor: AppColors.accent,
              ),
              enableActiveFill: true,
              onCompleted: (v) { setState(() => _code = v); _verify(); },
              onChanged: (v) => setState(() => _code = v),
            ),

            const SizedBox(height: AppSpacing.lg),
            SizedBox(
              width: double.infinity, height: 52,
              child: ElevatedButton(
                onPressed: _code.length == 6 ? _verify : null,
                child: const Text('Verify Code'),
              ),
            ),

            const SizedBox(height: AppSpacing.lg),
            Center(child: GestureDetector(
              onTap: _resendCountdown == 0 ? _resend : null,
              child: RichText(text: TextSpan(children: [
                const TextSpan(text: "Didn't receive it? ",
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
                TextSpan(
                  text: _resendCountdown > 0
                      ? 'Resend in ${_resendCountdown}s'
                      : 'Resend Code',
                  style: TextStyle(
                    color: _resendCountdown > 0
                        ? AppColors.textSecondary : AppColors.primary,
                    fontWeight: FontWeight.w700, fontSize: 14),
                ),
              ])),
            )),

            const SizedBox(height: AppSpacing.xl),
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.surfaceLight, borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.border)),
              child: const Row(children: [
                Icon(Icons.timer_outlined, color: AppColors.textSecondary, size: 16),
                SizedBox(width: 8),
                Expanded(child: Text('Code expires in 5 minutes',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 12))),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}
