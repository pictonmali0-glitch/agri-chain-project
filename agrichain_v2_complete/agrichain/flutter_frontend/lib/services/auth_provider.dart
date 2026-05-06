// lib/services/auth_provider.dart
import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import 'api_service.dart';

class UserModel {
  final String id;
  final String name;
  final String email;
  final String role;
  final bool isVerified;
  final String? profilePic;
  final String? location;
  final bool fingerprintEnabled;

  const UserModel({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    required this.isVerified,
    this.profilePic,
    this.location,
    this.fingerprintEnabled = false,
  });

  factory UserModel.fromJson(Map<String, dynamic> j) => UserModel(
        id: j['id'] ?? '',
        name: j['name'] ?? '',
        email: j['email'] ?? '',
        role: j['role'] ?? 'farmer',
        isVerified: j['is_verified'] ?? false,
        profilePic: j['profile_pic'],
        location: j['location'],
        fingerprintEnabled: j['fingerprint_enabled'] ?? false,
      );

  bool get isFarmer   => role == 'farmer';
  bool get isReceiver => role == 'receiver';
  bool get isAdmin    => role == 'admin';
}

class AuthProvider extends ChangeNotifier {
  UserModel? _user;
  bool _loading = false;
  String? _error;
  final _localAuth = LocalAuthentication();

  UserModel? get user     => _user;
  bool get loading        => _loading;
  String? get error       => _error;
  bool get isLoggedIn     => _user != null;

  void _setLoading(bool v) { _loading = v; notifyListeners(); }
  void _setError(String? e) { _error = e; notifyListeners(); }

  // ── Login ──────────────────────────────────────────────────
  Future<bool> login(String email, String password) async {
    _setLoading(true); _setError(null);
    final res = await ApiService.login(email, password);
    _setLoading(false);
    if (res.success) {
      await ApiService.saveTokens(
        res.data['access_token'], res.data['refresh_token']);
      _user = UserModel.fromJson(res.data['user']);
      notifyListeners();
      return true;
    }
    _setError(res.errorMessage);
    return false;
  }

  // ── Biometric login ─────────────────────────────────────────
  Future<bool> biometricLogin() async {
    try {
      final canCheck = await _localAuth.canCheckBiometrics;
      if (!canCheck) return false;
      final authenticated = await _localAuth.authenticate(
        localizedReason: 'Scan fingerprint to access AgriChain',
        options: const AuthenticationOptions(biometricOnly: true),
      );
      if (authenticated) {
        // Restore session from stored token
        final res = await ApiService.getMe();
        if (res.success) {
          _user = UserModel.fromJson(res.data);
          notifyListeners();
          return true;
        }
      }
    } catch (_) {}
    return false;
  }

  // ── Register ───────────────────────────────────────────────
  Future<bool> register(Map<String, dynamic> data) async {
    _setLoading(true); _setError(null);
    final res = await ApiService.register(data);
    _setLoading(false);
    if (res.success) {
      await ApiService.saveTokens(
        res.data['access_token'], res.data['refresh_token']);
      _user = UserModel.fromJson(res.data['user']);
      notifyListeners();
      return true;
    }
    _setError(res.errorMessage);
    return false;
  }

  // ── Restore session ────────────────────────────────────────
  Future<void> restoreSession() async {
    _setLoading(true);
    final token = await ApiService.getToken();
    if (token != null) {
      final res = await ApiService.getMe();
      if (res.success) {
        _user = UserModel.fromJson(res.data);
      } else {
        await ApiService.clearTokens();
      }
    }
    _setLoading(false);
  }

  // ── Logout ─────────────────────────────────────────────────
  Future<void> logout() async {
    await ApiService.clearTokens();
    _user = null;
    notifyListeners();
  }

  // ── Check biometric availability ───────────────────────────
  Future<bool> isBiometricAvailable() async {
    try {
      return await _localAuth.canCheckBiometrics;
    } catch (_) {
      return false;
    }
  }
}
