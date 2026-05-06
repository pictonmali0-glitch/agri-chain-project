// lib/screens/shared/profile_screen.dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import '../../services/auth_provider.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _nameCtrl     = TextEditingController();
  final _phoneCtrl    = TextEditingController();
  final _locationCtrl = TextEditingController();
  bool _loading = false;
  bool _fingerprint = false;

  @override
  void initState() {
    super.initState();
    final user = context.read<AuthProvider>().user;
    if (user != null) {
      _nameCtrl.text     = user.name;
      _phoneCtrl.text    = user.phone ?? '';  // If exposed
      _locationCtrl.text = user.location ?? '';
      _fingerprint       = user.fingerprintEnabled;
    }
  }

  Future<void> _pickPhoto() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 80);
    if (picked != null) {
      setState(() => _loading = true);
      await ApiService.uploadProfilePic(File(picked.path));
      // Refresh user
      final res = await ApiService.getMe();
      setState(() => _loading = false);
    }
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    await ApiService.updateProfile({
      'name': _nameCtrl.text.trim(),
      'phone': _phoneCtrl.text.trim(),
      'location': _locationCtrl.text.trim(),
      'fingerprint_enabled': _fingerprint,
    });
    setState(() => _loading = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile updated!'),
            backgroundColor: AppColors.primary));
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose(); _phoneCtrl.dispose(); _locationCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Profile Settings'),
        actions: [
          TextButton(onPressed: _loading ? null : _save,
              child: const Text('Save', style: TextStyle(
                  color: AppColors.primary, fontWeight: FontWeight.w700))),
        ],
      ),
      body: LoadingOverlay(
        isLoading: _loading,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(children: [
            // Avatar
            GestureDetector(
              onTap: _pickPhoto,
              child: Stack(alignment: Alignment.bottomRight, children: [
                CircleAvatar(
                  radius: 48,
                  backgroundColor: AppColors.primary.withOpacity(0.15),
                  child: Text(user?.name.substring(0, 1).toUpperCase() ?? '?',
                      style: const TextStyle(color: AppColors.primary, fontSize: 36,
                          fontWeight: FontWeight.w800)),
                ),
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: const BoxDecoration(
                    color: AppColors.primary, shape: BoxShape.circle),
                  child: const Icon(Icons.camera_alt_rounded, color: Colors.black, size: 14),
                ),
              ]),
            ),
            const SizedBox(height: 8),
            Text(user?.name ?? '', style: const TextStyle(
              color: AppColors.textPrimary, fontSize: 18, fontWeight: FontWeight.w700)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              margin: const EdgeInsets.only(top: 4),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.primary.withOpacity(0.3))),
              child: Text(user?.role.toUpperCase() ?? '',
                  style: const TextStyle(color: AppColors.primary,
                      fontSize: 11, fontWeight: FontWeight.w700)),
            ),
            const SizedBox(height: AppSpacing.xl),

            AppTextField(
              label: 'Full Name',
              controller: _nameCtrl,
              prefixIcon: const Icon(Icons.person_outline, color: AppColors.primary),
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
              controller: _locationCtrl,
              prefixIcon: const Icon(Icons.location_on_outlined, color: AppColors.primary),
            ),
            const SizedBox(height: AppSpacing.lg),

            // Biometric toggle
            Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.cardBg, borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.border)),
              child: Row(children: [
                const Icon(Icons.fingerprint_rounded, color: AppColors.primary, size: 28),
                const SizedBox(width: 14),
                const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Fingerprint Login', style: TextStyle(
                    color: AppColors.textPrimary, fontWeight: FontWeight.w600)),
                  Text('Use biometrics to sign in quickly',
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                ])),
                Switch(
                  value: _fingerprint,
                  onChanged: (v) => setState(() => _fingerprint = v),
                  activeColor: AppColors.primary,
                ),
              ]),
            ),
            const SizedBox(height: AppSpacing.xl),

            // Logout
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () async {
                  await context.read<AuthProvider>().logout();
                  if (context.mounted) context.go('/login');
                },
                icon: const Icon(Icons.logout_rounded, color: AppColors.error),
                label: const Text('Sign Out', style: TextStyle(color: AppColors.error)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.error),
                  shape: RoundedRectangleBorder(borderRadius: AppRadius.card),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}
