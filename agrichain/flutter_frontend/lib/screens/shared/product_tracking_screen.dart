// lib/screens/shared/product_tracking_screen.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class ProductTrackingScreen extends StatefulWidget {
  final String productId;
  const ProductTrackingScreen({super.key, required this.productId});
  @override
  State<ProductTrackingScreen> createState() => _ProductTrackingScreenState();
}

class _ProductTrackingScreenState extends State<ProductTrackingScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;
  Map? _product;
  List _timeline = [];
  List _chain = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final [histRes, chainRes] = await Future.wait([
      ApiService.getProductHistory(widget.productId),
      ApiService.getProductChain(widget.productId),
    ]);
    if (mounted) setState(() {
      if (histRes.success) {
        _product  = histRes.data['product'];
        _timeline = histRes.data['timeline'] ?? [];
      }
      if (chainRes.success) _chain = chainRes.data['chain'] ?? [];
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
        title: Text(_product?['name'] ?? 'Product Tracking'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        bottom: TabBar(
          controller: _tabs,
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.textSecondary,
          indicatorColor: AppColors.primary,
          tabs: const [
            Tab(text: 'Overview'),
            Tab(text: 'Timeline'),
            Tab(text: 'Blockchain'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : TabBarView(controller: _tabs, children: [
              _buildOverview(),
              _buildTimeline(),
              _buildChain(),
            ]),
    );
  }

  Widget _buildOverview() {
    if (_product == null) return EmptyState(message: 'Product not found', icon: Icons.error_outline);
    final farmer = _product!['farmer'];
    final batch = _product!['batch_number'] ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Product card
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [AppColors.primaryDark.withOpacity(0.5), AppColors.surface],
              begin: Alignment.topLeft, end: Alignment.bottomRight),
            borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.eco_rounded, color: AppColors.primary, size: 32),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_product!['name'] ?? '', style: const TextStyle(
                  color: AppColors.textPrimary, fontSize: 22, fontWeight: FontWeight.w800)),
                Text(batch, style: const TextStyle(
                  color: AppColors.primary, fontSize: 13, fontFamily: 'monospace')),
              ])),
              StatusBadge(status: _product!['status'] ?? 'pending'),
            ]),
          ]),
        ),
        const SizedBox(height: AppSpacing.md),

        // Details grid
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2, crossAxisSpacing: 10, mainAxisSpacing: 10,
          childAspectRatio: 2.2,
          children: [
            InfoCard(label: 'Quantity', value: '${_product!['quantity']} ${_product!['unit']}',
                icon: Icons.scale_rounded),
            InfoCard(label: 'Category', value: _product!['category'] ?? 'N/A',
                icon: Icons.category_rounded),
            InfoCard(label: 'Origin', value: _product!['origin'] ?? 'N/A',
                icon: Icons.location_on_rounded),
            InfoCard(label: 'Current Location',
                value: _product!['current_location'] ?? 'Unknown',
                icon: Icons.my_location_rounded, iconColor: AppColors.inTransit),
          ],
        ),
        const SizedBox(height: AppSpacing.md),

        // Farmer info
        if (farmer != null) ...[
          const SectionHeader(title: 'Farmer Information'),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.cardBg, borderRadius: AppRadius.card,
              border: Border.all(color: AppColors.border)),
            child: Row(children: [
              CircleAvatar(
                backgroundColor: AppColors.primary.withOpacity(0.15),
                child: Text(farmer['name']?.substring(0, 1).toUpperCase() ?? 'F',
                    style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
              ),
              const SizedBox(width: 12),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(farmer['name'] ?? '', style: const TextStyle(
                  color: AppColors.textPrimary, fontWeight: FontWeight.w600)),
                Text(farmer['email'] ?? '', style: const TextStyle(
                  color: AppColors.textSecondary, fontSize: 12)),
                if (farmer['location'] != null)
                  Text('📍 ${farmer['location']}', style: const TextStyle(
                    color: AppColors.primary, fontSize: 12)),
              ]),
            ]),
          ),
        ],
        const SizedBox(height: AppSpacing.md),

        // Harvest date
        if (_product!['harvest_date'] != null) ...[
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.cardBg, borderRadius: AppRadius.card,
              border: Border.all(color: AppColors.border)),
            child: Row(children: [
              const Icon(Icons.calendar_today_rounded, color: AppColors.primary),
              const SizedBox(width: 10),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Harvest Date', style: TextStyle(
                  color: AppColors.textSecondary, fontSize: 12)),
                Text(_product!['harvest_date'] ?? '', style: const TextStyle(
                  color: AppColors.textPrimary, fontWeight: FontWeight.w600)),
              ]),
            ]),
          ),
          const SizedBox(height: AppSpacing.md),
        ],

        // QR Code
        const SectionHeader(title: 'Product QR Code'),
        const SizedBox(height: 8),
        Center(
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white, borderRadius: AppRadius.card),
            child: QrImageView(
              data: '{"product_id":"${widget.productId}","batch":"$batch","type":"AGRICHAIN_PRODUCT"}',
              version: QrVersions.auto,
              size: 180,
            ),
          ),
        ),
      ]),
    );
  }

  Widget _buildTimeline() {
    if (_timeline.isEmpty) return EmptyState(
      message: 'No tracking history yet', icon: Icons.timeline_rounded);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(children: [
        ..._timeline.asMap().map((i, t) => MapEntry(i, TimelineStep(
          step: t, isFirst: i == 0, isLast: i == _timeline.length - 1))).values,
      ]),
    );
  }

  Widget _buildChain() {
    if (_chain.isEmpty) return EmptyState(
      message: 'No blockchain records yet', icon: Icons.link_off_rounded);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(children: [
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          margin: const EdgeInsets.only(bottom: AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.accent.withOpacity(0.08),
            borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.accent.withOpacity(0.3))),
          child: Row(children: [
            const Icon(Icons.verified_rounded, color: AppColors.accent, size: 18),
            const SizedBox(width: 8),
            Text('${_chain.length} block(s) on chain',
                style: const TextStyle(color: AppColors.accent)),
          ]),
        ),
        ..._chain.asMap().map((i, item) {
          final block = item['block'] as Map<String, dynamic>;
          return MapEntry(i, BlockCard(block: block, isLast: i == _chain.length - 1));
        }).values,
      ]),
    );
  }
}
