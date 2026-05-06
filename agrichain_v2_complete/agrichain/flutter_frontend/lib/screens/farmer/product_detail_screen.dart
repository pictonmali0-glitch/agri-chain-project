// lib/screens/farmer/product_detail_screen.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class ProductDetailScreen extends StatefulWidget {
  final String productId;
  const ProductDetailScreen({super.key, required this.productId});
  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;
  Map? _product;
  List _timeline = [];
  String? _qrBase64;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final [detailRes, histRes] = await Future.wait([
      ApiService.getProduct(widget.productId),
      ApiService.getProductHistory(widget.productId),
    ]);
    if (mounted) setState(() {
      if (detailRes.success) {
        _product   = detailRes.data['product'];
        _qrBase64  = detailRes.data['qr_base64'];
      }
      if (histRes.success) _timeline = histRes.data['timeline'] ?? [];
      _loading = false;
    });
  }

  @override
  void dispose() { _tabs.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(_product?['name'] ?? 'Product'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/farmer'),
        ),
        actions: [
          if (_product != null)
            IconButton(
              icon: const Icon(Icons.send_rounded),
              tooltip: 'Transfer Product',
              onPressed: () => context.go('/farmer/transfer/${widget.productId}'),
            ),
        ],
        bottom: TabBar(
          controller: _tabs,
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.textSecondary,
          indicatorColor: AppColors.primary,
          tabs: const [
            Tab(text: 'Details'),
            Tab(text: 'QR Code'),
            Tab(text: 'History'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : TabBarView(controller: _tabs, children: [
              _buildDetails(),
              _buildQr(),
              _buildHistory(),
            ]),
    );
  }

  // ── Details tab ──────────────────────────────────────────
  Widget _buildDetails() {
    if (_product == null) return EmptyState(message: 'Product not found', icon: Icons.error_outline);

    final images = (_product!['images'] as List?) ?? [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Status header
        Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [AppColors.primaryDark.withOpacity(0.5), AppColors.cardBg],
              begin: Alignment.topLeft, end: Alignment.bottomRight),
            borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border)),
          child: Row(children: [
            Container(
              width: 52, height: 52,
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.eco_rounded, color: AppColors.primary, size: 28),
            ),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_product!['name'] ?? '', style: const TextStyle(
                color: AppColors.textPrimary, fontSize: 20, fontWeight: FontWeight.w800)),
              const SizedBox(height: 2),
              Text(_product!['batch_number'] ?? '', style: const TextStyle(
                color: AppColors.primary, fontSize: 12, fontFamily: 'monospace')),
            ])),
            StatusBadge(status: _product!['status'] ?? 'pending'),
          ]),
        ),
        const SizedBox(height: AppSpacing.md),

        // Product images
        if (images.isNotEmpty) ...[
          const SectionHeader(title: 'Product Images'),
          const SizedBox(height: 8),
          SizedBox(
            height: 130,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: images.length,
              itemBuilder: (_, i) => Container(
                width: 130, height: 130,
                margin: const EdgeInsets.only(right: 8),
                decoration: BoxDecoration(
                  color: AppColors.cardBg,
                  borderRadius: AppRadius.card,
                  border: Border.all(color: AppColors.border),
                  image: DecorationImage(
                    image: NetworkImage('http://localhost:5000/${images[i]}'),
                    fit: BoxFit.cover,
                    onError: (_, __) {},
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],

        // Info grid
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2, crossAxisSpacing: 10, mainAxisSpacing: 10,
          childAspectRatio: 2.0,
          children: [
            InfoCard(label: 'Quantity',
                value: '${_product!['quantity']} ${_product!['unit']}',
                icon: Icons.scale_rounded),
            InfoCard(label: 'Category',
                value: _product!['category'] ?? 'N/A',
                icon: Icons.category_rounded),
            InfoCard(label: 'Origin',
                value: _product!['origin'] ?? 'N/A',
                icon: Icons.location_on_rounded),
            InfoCard(label: 'Current Location',
                value: _product!['current_location'] ?? 'Unknown',
                icon: Icons.my_location_rounded, iconColor: AppColors.inTransit),
          ],
        ),
        const SizedBox(height: AppSpacing.md),

        // Harvest date
        if (_product!['harvest_date'] != null)
          _infoRow(Icons.calendar_today_rounded, 'Harvest Date', _product!['harvest_date']),

        // Description
        if ((_product!['description'] ?? '').isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.cardBg, borderRadius: AppRadius.card,
              border: Border.all(color: AppColors.border)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Row(children: [
                Icon(Icons.notes_rounded, color: AppColors.primary, size: 16),
                SizedBox(width: 8),
                Text('Description', style: TextStyle(
                  color: AppColors.textSecondary, fontSize: 12)),
              ]),
              const SizedBox(height: 6),
              Text(_product!['description'], style: const TextStyle(
                color: AppColors.textPrimary, fontSize: 14)),
            ]),
          ),
        ],
        const SizedBox(height: AppSpacing.md),

        // Current holder
        if (_product!['current_holder'] != null) ...[
          _infoRow(Icons.person_pin_rounded, 'Current Holder',
              _product!['current_holder']['name']),
        ],

        // Created
        _infoRow(Icons.access_time_rounded, 'Added',
            _product!['created_at']?.toString().substring(0, 10) ?? ''),

        const SizedBox(height: AppSpacing.xl),

        // Action buttons
        Row(children: [
          Expanded(
            child: ElevatedButton.icon(
              onPressed: () => context.go('/farmer/transfer/${widget.productId}'),
              icon: const Icon(Icons.send_rounded),
              label: const Text('Transfer'),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => _tabs.animateTo(2),
              icon: const Icon(Icons.timeline_rounded, color: AppColors.primary),
              label: const Text('History', style: TextStyle(color: AppColors.primary)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.primary),
                shape: RoundedRectangleBorder(borderRadius: AppRadius.card),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
        ]),
      ]),
    );
  }

  Widget _infoRow(IconData icon, String label, String value) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.cardBg, borderRadius: AppRadius.card,
        border: Border.all(color: AppColors.border)),
      child: Row(children: [
        Icon(icon, color: AppColors.primary, size: 18),
        const SizedBox(width: 12),
        Text('$label: ', style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
        Expanded(child: Text(value, style: const TextStyle(
          color: AppColors.textPrimary, fontSize: 13, fontWeight: FontWeight.w500),
          overflow: TextOverflow.ellipsis)),
      ]),
    );
  }

  // ── QR tab ────────────────────────────────────────────────
  Widget _buildQr() {
    final batch = _product?['batch_number'] ?? '';
    final qrData = jsonEncode({
      'type': 'AGRICHAIN_PRODUCT',
      'product_id': widget.productId,
      'batch': batch,
      'verify_url': 'https://agrichain.app/verify/${widget.productId}',
    });

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(children: [
        const SizedBox(height: AppSpacing.md),
        Text(_product?['name'] ?? '', style: const TextStyle(
          color: AppColors.textPrimary, fontSize: 22, fontWeight: FontWeight.w800)),
        Text(batch, style: const TextStyle(
          color: AppColors.primary, fontSize: 13, fontFamily: 'monospace')),
        const SizedBox(height: AppSpacing.xl),

        // QR Code widget
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white, borderRadius: AppRadius.card,
            boxShadow: [BoxShadow(
              color: AppColors.primary.withOpacity(0.3),
              blurRadius: 20, spreadRadius: 2)]),
          child: Column(children: [
            QrImageView(
              data: qrData,
              version: QrVersions.auto,
              size: 220,
              gapless: false,
              embeddedImage: const AssetImage('assets/images/logo_small.png'),
              embeddedImageStyle: const QrEmbeddedImageStyle(size: Size(32, 32)),
            ),
            const SizedBox(height: 12),
            Text(batch, style: const TextStyle(
              color: Colors.black54, fontSize: 11, fontFamily: 'monospace')),
          ]),
        ),
        const SizedBox(height: AppSpacing.lg),

        // Instructions
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.surfaceLight, borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border)),
          child: const Column(children: [
            Row(children: [
              Icon(Icons.info_outline_rounded, color: AppColors.primary, size: 16),
              SizedBox(width: 8),
              Text('QR Code Instructions', style: TextStyle(
                color: AppColors.primary, fontWeight: FontWeight.w700, fontSize: 13)),
            ]),
            SizedBox(height: 8),
            Text(
              '• Print and attach this QR code to the product packaging\n'
              '• Receivers can scan it at any transfer point\n'
              '• Each scan records location and timestamp on blockchain\n'
              '• The QR is unique to this batch – cannot be duplicated',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12, height: 1.6),
            ),
          ]),
        ),
        const SizedBox(height: AppSpacing.md),

        // Copy QR data button
        OutlinedButton.icon(
          onPressed: () {
            Clipboard.setData(ClipboardData(text: qrData));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('QR data copied to clipboard'),
                  backgroundColor: AppColors.primary));
          },
          icon: const Icon(Icons.copy_rounded, color: AppColors.primary),
          label: const Text('Copy QR Data', style: TextStyle(color: AppColors.primary)),
          style: OutlinedButton.styleFrom(
            side: const BorderSide(color: AppColors.primary),
            shape: RoundedRectangleBorder(borderRadius: AppRadius.card),
          ),
        ),
      ]),
    );
  }

  // ── History tab ───────────────────────────────────────────
  Widget _buildHistory() {
    if (_timeline.isEmpty) {
      return EmptyState(
        message: 'No transfers yet.\nThis product has not been moved.',
        icon: Icons.timeline_rounded,
        actionLabel: 'Transfer Product',
        onAction: () => context.go('/farmer/transfer/${widget.productId}'),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Summary bar
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          margin: const EdgeInsets.only(bottom: AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.cardBg, borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border)),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _summaryItem('${_timeline.length}', 'Transfers'),
              Container(width: 1, height: 32, color: AppColors.border),
              _summaryItem(
                  _timeline.where((t) => t['status'] == 'acknowledged').length.toString(),
                  'Acknowledged'),
              Container(width: 1, height: 32, color: AppColors.border),
              _summaryItem(_product?['current_location'] ?? 'N/A', 'Current'),
            ],
          ),
        ),

        const SectionHeader(title: 'Transfer Timeline'),
        const SizedBox(height: 10),
        ..._timeline.asMap().map((i, t) => MapEntry(i, TimelineStep(
          step: t,
          isFirst: i == 0,
          isLast: i == _timeline.length - 1,
        ))).values,
      ]),
    );
  }

  Widget _summaryItem(String value, String label) => Column(children: [
    Text(value, style: const TextStyle(
      color: AppColors.primary, fontSize: 16, fontWeight: FontWeight.w800),
      maxLines: 1, overflow: TextOverflow.ellipsis),
    Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 11)),
  ]);
}
