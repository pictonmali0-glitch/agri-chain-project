// lib/screens/receiver/receiver_dashboard.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../../services/auth_provider.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class ReceiverDashboard extends StatefulWidget {
  const ReceiverDashboard({super.key});
  @override
  State<ReceiverDashboard> createState() => _ReceiverDashboardState();
}

class _ReceiverDashboardState extends State<ReceiverDashboard> {
  int _selectedIndex = 0;
  List _pending = [];
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    final res = await ApiService.getPendingTransfers();
    if (mounted) setState(() {
      if (res.success) _pending = res.data['pending'] ?? [];
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Row(children: [
          const AgriLogo(size: 30),
          const SizedBox(width: 10),
          const Text('AgriChain'),
        ]),
        actions: [
          IconButton(icon: const Icon(Icons.person_outline),
              onPressed: () => context.go('/profile')),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.primary, onRefresh: _load,
        child: _buildBody(user),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (i) => setState(() => _selectedIndex = i),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.qr_code_scanner_rounded), label: 'Scan QR'),
          BottomNavigationBarItem(icon: Icon(Icons.inbox_rounded), label: 'Pending'),
          BottomNavigationBarItem(icon: Icon(Icons.track_changes_rounded), label: 'Track'),
        ],
      ),
    );
  }

  Widget _buildBody(user) {
    if (_loading) return const Center(child: CircularProgressIndicator(color: AppColors.primary));
    switch (_selectedIndex) {
      case 0: return _buildHome(user);
      case 1: return _buildScanner();
      case 2: return _buildPending();
      case 3: return _buildSearch();
      default: return _buildHome(user);
    }
  }

  // ── Home ─────────────────────────────────────────────────
  Widget _buildHome(user) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Greeting
        Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [AppColors.inTransit.withOpacity(0.3), AppColors.surface],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border),
          ),
          child: Row(children: [
            CircleAvatar(
              radius: 26,
              backgroundColor: AppColors.inTransit.withOpacity(0.2),
              child: Text(user?.name.substring(0, 1).toUpperCase() ?? 'R',
                style: const TextStyle(color: AppColors.inTransit, fontSize: 20,
                    fontWeight: FontWeight.w800)),
            ),
            const SizedBox(width: 14),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Receiver Portal', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
              Text(user?.name ?? 'Receiver', style: const TextStyle(
                color: AppColors.textPrimary, fontSize: 18, fontWeight: FontWeight.w700)),
            ]),
          ]),
        ),
        const SizedBox(height: AppSpacing.lg),

        // Stats
        Row(children: [
          Expanded(child: StatCard(
            title: 'Pending', value: '${_pending.length}',
            icon: Icons.hourglass_empty_rounded, color: AppColors.accentAmber)),
          const SizedBox(width: 10),
          Expanded(child: StatCard(
            title: 'Acknowledged', value: '${_pending.where((t) => t['status'] == 'acknowledged').length}',
            icon: Icons.verified_rounded, color: AppColors.acknowledged)),
        ]),
        const SizedBox(height: AppSpacing.lg),

        // Quick actions
        const SectionHeader(title: 'Quick Actions'),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(child: _actionCard('Scan QR', Icons.qr_code_scanner_rounded,
              AppColors.primary, () => setState(() => _selectedIndex = 1))),
          const SizedBox(width: 10),
          Expanded(child: _actionCard('Pending (${_pending.length})',
              Icons.inbox_rounded, AppColors.accentAmber,
              () => setState(() => _selectedIndex = 2))),
        ]),
        const SizedBox(height: AppSpacing.lg),

        // Pending list preview
        if (_pending.isNotEmpty) ...[
          SectionHeader(title: 'Incoming Transfers', action: 'See All',
              onAction: () => setState(() => _selectedIndex = 2)),
          const SizedBox(height: 10),
          ..._pending.take(3).map((t) => _pendingCard(t)),
        ],
      ]),
    );
  }

  Widget _actionCard(String label, IconData icon, Color color, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1), borderRadius: AppRadius.card,
          border: Border.all(color: color.withOpacity(0.3))),
        child: Column(children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(height: 8),
          Text(label, style: TextStyle(color: color, fontWeight: FontWeight.w600),
              textAlign: TextAlign.center),
        ]),
      ),
    );
  }

  // ── QR Scanner ────────────────────────────────────────────
  Widget _buildScanner() {
    return Column(children: [
      Expanded(
        flex: 3,
        child: Stack(children: [
          MobileScanner(
            onDetect: (capture) {
              final barcode = capture.barcodes.firstOrNull;
              if (barcode?.rawValue != null) {
                _onQrDetected(barcode!.rawValue!);
              }
            },
          ),
          // Overlay
          Center(
            child: Container(
              width: 250, height: 250,
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.primary, width: 3),
                borderRadius: BorderRadius.circular(16),
              ),
            ),
          ),
          const Positioned(
            bottom: 20, left: 0, right: 0,
            child: Text('Point camera at product QR code',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white, fontSize: 14,
                  shadows: [Shadow(blurRadius: 6, color: Colors.black)])),
          ),
        ]),
      ),
      // Manual entry
      Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(children: [
          const Text('Or search by Batch Number:',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: _searchController()),
          ]),
        ]),
      ),
    ]);
  }

  final _batchCtrl = TextEditingController();
  Widget _searchController() {
    return Row(children: [
      Expanded(
        child: TextField(
          controller: _batchCtrl,
          style: const TextStyle(color: AppColors.textPrimary),
          decoration: InputDecoration(
            hintText: 'Enter batch number...',
            hintStyle: const TextStyle(color: AppColors.textSecondary),
            filled: true, fillColor: AppColors.surfaceLight,
            border: OutlineInputBorder(borderRadius: AppRadius.card,
                borderSide: const BorderSide(color: AppColors.border)),
          ),
        ),
      ),
      const SizedBox(width: 8),
      ElevatedButton(
        onPressed: () => _onQrDetected('{"batch":"${_batchCtrl.text.trim()}"}'),
        child: const Text('Scan'),
      ),
    ]);
  }

  Future<void> _onQrDetected(String rawValue) async {
    try {
      final payload = <String, dynamic>{};
      // Try parsing JSON
      if (rawValue.startsWith('{')) {
        final decoded = jsonDecode(rawValue) as Map<String, dynamic>;
        payload.addAll(decoded);
      } else {
        payload['product_id'] = rawValue;
      }

      final res = await ApiService.scanQr(payload);
      if (res.success && mounted) {
        _showProductSheet(res.data);
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res.errorMessage ?? 'Product not found'),
              backgroundColor: AppColors.error));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Invalid QR code'),
              backgroundColor: AppColors.error));
      }
    }
  }

  void _showProductSheet(Map data) {
    final product = data['product'] as Map;
    final timeline = data['timeline'] as List;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => DraggableScrollableSheet(
        initialChildSize: 0.85, maxChildSize: 0.95, minChildSize: 0.5,
        expand: false,
        builder: (_, ctrl) => ListView(controller: ctrl, padding: const EdgeInsets.all(AppSpacing.lg), children: [
          Center(child: Container(
            width: 40, height: 4,
            decoration: BoxDecoration(
              color: AppColors.border, borderRadius: BorderRadius.circular(2)))),
          const SizedBox(height: 16),
          const Text('Product Verified ✓', style: TextStyle(
            color: AppColors.accent, fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(product['name'] ?? '', style: const TextStyle(
            color: AppColors.textPrimary, fontSize: 22, fontWeight: FontWeight.w800)),
          Text('Batch: ${product['batch_number']}', style: const TextStyle(
            color: AppColors.primary, fontFamily: 'monospace')),
          const SizedBox(height: 16),
          if (data['farmer'] != null) ...[
            _infoRow('Farmer', data['farmer']['name']),
            _infoRow('Farm Location', data['farmer']['location'] ?? 'N/A'),
          ],
          _infoRow('Status', product['status']),
          _infoRow('Current Location', product['current_location'] ?? 'N/A'),
          const SizedBox(height: 20),
          const Text('Tracking Timeline', style: TextStyle(
            color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 10),
          ...timeline.asMap().map((i, t) => MapEntry(i,
            TimelineStep(step: t, isFirst: i == 0, isLast: i == timeline.length - 1))).values,
          const SizedBox(height: 20),
          // Acknowledge button (if in_transit to this receiver)
          ElevatedButton.icon(
            onPressed: () {
              Navigator.pop(context);
              _showAckDialog(product);
            },
            icon: const Icon(Icons.verified_rounded),
            label: const Text('Acknowledge Receipt'),
          ),
        ]),
      ),
    );
  }

  Widget _infoRow(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(children: [
      Text('$label: ', style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
      Expanded(child: Text(value, style: const TextStyle(color: AppColors.textPrimary, fontSize: 13))),
    ]),
  );

  void _showAckDialog(Map product) {
    final qtyCtrl = TextEditingController(text: '${product['quantity']}');
    final noteCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Acknowledge Receipt', style: TextStyle(color: AppColors.textPrimary)),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          AppTextField(label: 'Quantity Received', controller: qtyCtrl,
              keyboardType: TextInputType.number),
          const SizedBox(height: 12),
          AppTextField(label: 'Notes (optional)', controller: noteCtrl, maxLines: 2),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context),
              child: const Text('Cancel', style: TextStyle(color: AppColors.textSecondary))),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              // Find the pending transfer for this product
              final pending = _pending.where((t) => t['product_id'] == product['id']).firstOrNull;
              if (pending != null) {
                await ApiService.acknowledgeTransfer(pending['id'], {
                  'quantity_received': double.tryParse(qtyCtrl.text) ?? product['quantity'],
                  'note': noteCtrl.text,
                });
                await _load();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Receipt acknowledged! Blockchain updated.'),
                        backgroundColor: AppColors.primary));
                }
              }
            },
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  // ── Pending transfers ─────────────────────────────────────
  Widget _buildPending() {
    if (_pending.isEmpty) return EmptyState(
      message: 'No pending transfers', icon: Icons.inbox_rounded);

    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: _pending.length,
      itemBuilder: (_, i) => _pendingCard(_pending[i]),
    );
  }

  Widget _pendingCard(Map t) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardBg, borderRadius: AppRadius.card,
        border: Border.all(color: AppColors.border)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(t['product']?['name'] ?? 'Product',
              style: const TextStyle(color: AppColors.textPrimary,
                  fontWeight: FontWeight.w700, fontSize: 15))),
          StatusBadge(status: t['status'] ?? 'in_transit'),
        ]),
        const SizedBox(height: 6),
        Text('From: ${t['sender']?['name'] ?? '?'} • ${t['from_location'] ?? '?'}',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
        Text('Qty: ${t['quantity_sent']} ${t['unit']}',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: OutlinedButton(
              onPressed: () => _showAckDialog(t['product'] ?? {}),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.accent),
                foregroundColor: AppColors.accent,
                shape: RoundedRectangleBorder(borderRadius: AppRadius.card),
              ),
              child: const Text('Acknowledge'),
            ),
          ),
          const SizedBox(width: 8),
          OutlinedButton(
            onPressed: () async {
              await ApiService.rejectTransfer(t['id'], 'Rejected by receiver');
              await _load();
            },
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: AppColors.error),
              foregroundColor: AppColors.error,
              shape: RoundedRectangleBorder(borderRadius: AppRadius.card),
            ),
            child: const Text('Reject'),
          ),
        ]),
      ]),
    );
  }

  // ── Product search / track ────────────────────────────────
  Widget _buildSearch() {
    return _ProductSearchTab();
  }
}

class _ProductSearchTab extends StatefulWidget {
  @override
  State<_ProductSearchTab> createState() => _ProductSearchTabState();
}

class _ProductSearchTabState extends State<_ProductSearchTab> {
  final _ctrl = TextEditingController();
  List _results = [];
  bool _loading = false;

  Future<void> _search(String q) async {
    if (q.isEmpty) return;
    setState(() => _loading = true);
    final res = await ApiService.searchProducts(q);
    setState(() {
      if (res.success) _results = res.data['results'] ?? [];
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: TextField(
          controller: _ctrl,
          onChanged: _search,
          style: const TextStyle(color: AppColors.textPrimary),
          decoration: InputDecoration(
            hintText: 'Search product, batch, farmer...',
            hintStyle: const TextStyle(color: AppColors.textSecondary),
            prefixIcon: const Icon(Icons.search_rounded, color: AppColors.primary),
            suffixIcon: _loading
                ? const Padding(
                    padding: EdgeInsets.all(12),
                    child: SizedBox(width: 18, height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary)))
                : null,
            filled: true, fillColor: AppColors.surfaceLight,
            border: OutlineInputBorder(borderRadius: AppRadius.card,
                borderSide: const BorderSide(color: AppColors.border)),
          ),
        ),
      ),
      Expanded(
        child: _results.isEmpty
            ? EmptyState(message: 'Search to track a product', icon: Icons.track_changes_rounded)
            : ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                itemCount: _results.length,
                itemBuilder: (_, i) {
                  final r = _results[i];
                  return ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    tileColor: AppColors.cardBg,
                    shape: RoundedRectangleBorder(
                      borderRadius: AppRadius.card,
                      side: const BorderSide(color: AppColors.border)),
                    leading: const Icon(Icons.eco_rounded, color: AppColors.primary),
                    title: Text('${r['name']}', style: const TextStyle(color: AppColors.textPrimary)),
                    subtitle: Text('${r['batch_number']} • ${r['farmer_name']}',
                        style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                    trailing: StatusBadge(status: r['status'] ?? 'pending'),
                    onTap: () => context.go('/track/${r['id']}'),
                  );
                },
              ),
      ),
    ]);
  }
}
