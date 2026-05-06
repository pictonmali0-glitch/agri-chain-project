// lib/services/api_service.dart
// Central HTTP client for AgriChain backend

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../utils/constants.dart';

class ApiService {
  static const _storage = FlutterSecureStorage();

  // ── Token management ────────────────────────────────────────
  static Future<String?> getToken() => _storage.read(key: 'access_token');
  static Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }
  static Future<void> clearTokens() async {
    await _storage.deleteAll();
  }

  static Future<Map<String, String>> _headers({bool auth = true}) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (auth) {
      final token = await getToken();
      if (token != null) headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  // ── Generic request helpers ─────────────────────────────────
  static Future<ApiResponse> get(String path) async {
    try {
      final res = await http
          .get(Uri.parse('$kBaseUrl$path'), headers: await _headers())
          .timeout(const Duration(seconds: 15));
      return ApiResponse.from(res);
    } catch (e) {
      return ApiResponse.error(_networkError(e));
    }
  }

  static Future<ApiResponse> post(String path, Map<String, dynamic> body,
      {bool auth = true}) async {
    try {
      final res = await http
          .post(
            Uri.parse('$kBaseUrl$path'),
            headers: await _headers(auth: auth),
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 15));
      return ApiResponse.from(res);
    } catch (e) {
      return ApiResponse.error(_networkError(e));
    }
  }

  static Future<ApiResponse> put(String path, Map<String, dynamic> body) async {
    try {
      final res = await http
          .put(
            Uri.parse('$kBaseUrl$path'),
            headers: await _headers(),
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 15));
      return ApiResponse.from(res);
    } catch (e) {
      return ApiResponse.error(_networkError(e));
    }
  }

  static Future<ApiResponse> uploadFile(
      String path, File file, String fieldName,
      {Map<String, String>? fields}) async {
    try {
      final token = await getToken();
      final req = http.MultipartRequest('POST', Uri.parse('$kBaseUrl$path'));
      if (token != null) req.headers['Authorization'] = 'Bearer $token';
      req.files.add(await http.MultipartFile.fromPath(fieldName, file.path));
      if (fields != null) req.fields.addAll(fields);
      final streamed = await req.send().timeout(const Duration(seconds: 30));
      final res = await http.Response.fromStream(streamed);
      return ApiResponse.from(res);
    } catch (e) {
      return ApiResponse.error(_networkError(e));
    }
  }

  static String _networkError(dynamic e) {
    if (e is SocketException) return 'No internet connection.';
    if (e.toString().contains('TimeoutException')) return 'Request timed out.';
    return 'Network error. Please try again.';
  }

  // ── AUTH ────────────────────────────────────────────────────
  static Future<ApiResponse> requestOtp(String email, String purpose) =>
      post('/auth/request-otp', {'email': email, 'purpose': purpose}, auth: false);

  static Future<ApiResponse> verifyOtp(String email, String code, String purpose) =>
      post('/auth/verify-otp', {'email': email, 'code': code, 'purpose': purpose}, auth: false);

  static Future<ApiResponse> register(Map<String, dynamic> data) =>
      post('/auth/register', data, auth: false);

  static Future<ApiResponse> login(String email, String password) =>
      post('/auth/login', {'email': email, 'password': password}, auth: false);

  static Future<ApiResponse> resetPassword(
          String email, String code, String newPassword) =>
      post('/auth/reset-password',
          {'email': email, 'otp_code': code, 'new_password': newPassword},
          auth: false);

  static Future<ApiResponse> getMe() => get('/auth/me');
  static Future<ApiResponse> updateProfile(Map<String, dynamic> data) =>
      put('/auth/profile', data);
  static Future<ApiResponse> uploadProfilePic(File file) =>
      uploadFile('/auth/profile/picture', file, 'file');

  // ── PRODUCTS ────────────────────────────────────────────────
  static Future<ApiResponse> createProduct(Map<String, dynamic> data) =>
      post('/products/', data);
  static Future<ApiResponse> listProducts({String search = '', String status = ''}) =>
      get('/products/?search=$search&status=$status');
  static Future<ApiResponse> getProduct(String id) => get('/products/$id');
  static Future<ApiResponse> searchProducts(String q) => get('/products/search?q=$q');
  static Future<ApiResponse> getProductHistory(String id) => get('/products/$id/history');
  static Future<ApiResponse> getProductQr(String id) => get('/products/$id/qr');
  static Future<ApiResponse> uploadProductImages(String productId, File file) =>
      uploadFile('/products/$productId/images', file, 'files');

  // ── TRANSFERS ───────────────────────────────────────────────
  static Future<ApiResponse> createTransfer(Map<String, dynamic> data) =>
      post('/transfers/', data);
  static Future<ApiResponse> acknowledgeTransfer(
          String transferId, Map<String, dynamic> data) =>
      post('/transfers/$transferId/acknowledge', data);
  static Future<ApiResponse> rejectTransfer(String transferId, String reason) =>
      post('/transfers/$transferId/reject', {'reason': reason});
  static Future<ApiResponse> listTransfers() => get('/transfers/');
  static Future<ApiResponse> getTransfer(String id) => get('/transfers/$id');

  // ── BLOCKCHAIN ──────────────────────────────────────────────
  static Future<ApiResponse> getChain({int page = 1}) =>
      get('/blockchain/chain?page=$page');
  static Future<ApiResponse> verifyChain() => get('/blockchain/verify');
  static Future<ApiResponse> getProductChain(String productId) =>
      get('/blockchain/product/$productId');
  static Future<ApiResponse> getChainStats() => get('/blockchain/stats');

  // ── ADMIN ───────────────────────────────────────────────────
  static Future<ApiResponse> getAdminDashboard() => get('/admin/dashboard');
  static Future<ApiResponse> getProductMovements() => get('/admin/movements');
  static Future<ApiResponse> getSuspiciousTransactions() => get('/admin/suspicious');
  static Future<ApiResponse> listAllUsers({String role = ''}) =>
      get('/admin/users?role=$role');
  static Future<ApiResponse> approveTransfer(String id, String action,
          {String reason = ''}) =>
      post('/admin/transfers/$id/approve', {'action': action, 'reason': reason});

  // ── RECEIVER ────────────────────────────────────────────────
  static Future<ApiResponse> scanQr(Map<String, dynamic> payload) =>
      post('/receiver/scan', payload);
  static Future<ApiResponse> getPendingTransfers() => get('/receiver/pending');
  static Future<ApiResponse> trackProduct(String productId) =>
      get('/receiver/track/$productId');
}

// ── ApiResponse wrapper ─────────────────────────────────────
class ApiResponse {
  final int statusCode;
  final Map<String, dynamic> data;
  final String? errorMessage;

  const ApiResponse({
    required this.statusCode,
    required this.data,
    this.errorMessage,
  });

  bool get success => statusCode >= 200 && statusCode < 300 && errorMessage == null;

  factory ApiResponse.from(http.Response res) {
    try {
      final decoded = jsonDecode(res.body) as Map<String, dynamic>;
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return ApiResponse(statusCode: res.statusCode, data: decoded);
      }
      return ApiResponse(
        statusCode: res.statusCode,
        data: decoded,
        errorMessage: decoded['error'] ?? decoded['message'] ?? 'Unknown error.',
      );
    } catch (_) {
      return ApiResponse(
        statusCode: res.statusCode,
        data: {},
        errorMessage: 'Failed to parse server response.',
      );
    }
  }

  factory ApiResponse.error(String message) => ApiResponse(
        statusCode: 0,
        data: {},
        errorMessage: message,
      );
}
