// lib/screens/farmer/farmer_dashboard.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../services/auth_provider.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class FarmerDashboard extends StatefulWidget {
  const FarmerDashboard({super.key});
  @override
  State<FarmerDashboard> createState() => _FarmerDashboardState();
}

class _FarmerDashboardState extends State<FarmerDashboard> {
  int _selectedIndex = 0;
  Map<String, dynamic>? _stats;
  List _products = [];
  List _transfers = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    final [prodRes, transRes] = await Future.wait([
      ApiService.listProducts(),
      ApiService.listTransfers(),
    ]);
    if (mounted) {
      setState(() {
        if (prodRes.success) _products = prodRes.data['products'] ?? [];
        if (transRes.success) _transfers = transRes.data['transfers'] ?? [];
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Row(children: [
          const AgriLogo(size: 32),
          const SizedBox(width: 10),
          const Text('AgriChain'),
        ]),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {},
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () => context.go('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.primary,
        onRefresh: _loadData,
        child: _buildBody(user),
      ),
      floatingActionButton: _selectedIndex == 0
          ? FloatingActionButton.extended(
              onPressed: () => context.go('/farmer/add-product'),
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.black,
              icon: const Icon(Icons.add_rounded),
              label: const Text('Add Product', style: TextStyle(fontWeight: FontWeight.w700)),
            )
          : null,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (i) => setState(() => _selectedIndex = i),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Dashboard'),
          BottomNavigationBarItem(icon: Icon(Icons.inventory_2_rounded), label: 'Products'),
          BottomNavigationBarItem(icon: Icon(Icons.swap_horiz_rounded), label: 'Transfers'),
          BottomNavigationBarItem(icon: Icon(Icons.link_rounded), label: 'Blockchain'),
        ],
      ),
    );
  }

  Widget _buildBody(user) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AppColors.primary));
    }
    switch (_selectedIndex) {
      case 0: return _buildHome(user);
      case 1: return _buildProducts();
      case 2: return _buildTransfers();
      case 3: return _buildBlockchain();
      default: return _buildHome(user);
    }
  }

  // ── Home tab ───────────────────────────────────────────────
  Widget _buildHome(user) {
    final total = _products.length;
    final inTransit = _products.where((p) => p['status'] == 'in_transit').length;
    final acknowledged = _products.where((p) => p['status'] == 'acknowledged').length;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Greeting
        Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [AppColors.primaryDark.withOpacity(0.6), AppColors.surface],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border),
          ),
          child: Row(children: [
            CircleAvatar(
              radius: 26,
              backgroundColor: AppColors.primary.withOpacity(0.2),
              child: Text(
                user?.name.substring(0, 1).toUpperCase() ?? 'F',
                style: const TextStyle(color: AppColors.primary, fontSize: 20,
                    fontWeight: FontWeight.w800),
              ),
            ),
            const SizedBox(width: 14),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Welcome back,', style: TextStyle(
                color: AppColors.textSecondary, fontSize: 13)),
              Text(user?.name ?? 'Farmer',
                  style: const TextStyle(color: AppColors.textPrimary,
                      fontSize: 18, fontWeight: FontWeight.w700)),
              Text(user?.location ?? 'Uganda',
                  style: const TextStyle(color: AppColors.primary, fontSize: 12)),
            ]),
          ]),
        ),
        const SizedBox(height: AppSpacing.lg),

        // Stats grid
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2, crossAxisSpacing: 10, mainAxisSpacing: 10,
          childAspectRatio: 1.4,
          children: [
            StatCard(title: 'Total Products', value: '$total',
                icon: Icons.inventory_2_rounded, color: AppColors.primary),
            StatCard(title: 'In Transit', value: '$inTransit',
                icon: Icons.local_shipping_rounded, color: AppColors.inTransit),
            StatCard(title: 'Acknowledged', value: '$acknowledged',
                icon: Icons.verified_rounded, color: AppColors.acknowledged),
            StatCard(title: 'Transfers', value: '${_transfers.length}',
                icon: Icons.swap_horiz_rounded, color: AppColors.accentAmber),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),

        // Recent products
        SectionHeader(
          title: 'Recent Products',
          action: 'View All',
          onAction: () => setState(() => _selectedIndex = 1),
        ),
        const SizedBox(height: 10),
        if (_products.isEmpty)
          EmptyState(
            message: 'No products yet.\nTap + to add your first crop.',
            icon: Icons.agriculture_rounded,
            actionLabel: 'Add Product',
            onAction: () => context.go('/farmer/add-product'),
          )
        else
          ..._products.take(3).map((p) => _productCard(p)),
      ]),
    );
  }

  // ── Products tab ───────────────────────────────────────────
  Widget _buildProducts() {
    return Column(children: [
      // Search bar
      Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: TextField(
          onChanged: (v) async {
            final res = await ApiService.searchProducts(v);
            if (res.success && mounted) {
              setState(() => _products = res.data['results'] ?? _products);
            }
          },
          style: const TextStyle(color: AppColors.textPrimary),
          decoration: InputDecoration(
            hintText: 'Search by name, batch, farmer...',
            hintStyle: const TextStyle(color: AppColors.textSecondary),
            prefixIcon: const Icon(Icons.search_rounded, color: AppColors.primary),
            filled: true,
            fillColor: AppColors.surfaceLight,
            border: OutlineInputBorder(
              borderRadius: AppRadius.card,
              borderSide: const BorderSide(color: AppColors.border),
            ),
          ),
        ),
      ),
      Expanded(
        child: _products.isEmpty
            ? EmptyState(message: 'No products found', icon: Icons.inventory_2_outlined)
            : ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                itemCount: _products.length,
                itemBuilder: (_, i) => _productCard(_products[i]),
              ),
      ),
    ]);
  }

  Widget _productCard(Map p) {
    return GestureDetector(
      onTap: () => context.go('/farmer/product/${p['id']}'),
      child: Container(
        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.cardBg,
          borderRadius: AppRadius.card,
          border: Border.all(color: AppColors.border),
        ),
        child: Row(children: [
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.eco_rounded, color: AppColors.primary),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(p['name'] ?? '', style: const TextStyle(
                color: AppColors.textPrimary, fontWeight: FontWeight.w600)),
              Text('${p['batch_number'] ?? ''} • ${p['quantity']} ${p['unit']}',
                  style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
              if (p['current_location'] != null)
                Text('📍 ${p['current_location']}',
                    style: const TextStyle(color: AppColors.primary, fontSize: 11)),
            ]),
          ),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            StatusBadge(status: p['status'] ?? 'pending'),
            const SizedBox(height: 4),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textSecondary, size: 18),
          ]),
        ]),
      ),
    );
  }

  // ── Transfers tab ──────────────────────────────────────────
  Widget _buildTransfers() {
    return _transfers.isEmpty
        ? EmptyState(message: 'No transfers yet', icon: Icons.swap_horiz_rounded)
        : ListView.builder(
            padding: const EdgeInsets.all(AppSpacing.md),
            itemCount: _transfers.length,
            itemBuilder: (_, i) {
              final t = _transfers[i];
              return Container(
                margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: t['is_suspicious'] == true
                      ? AppColors.suspicious.withOpacity(0.05) : AppColors.cardBg,
                  borderRadius: AppRadius.card,
                  border: Border.all(
                    color: t['is_suspicious'] == true
                        ? AppColors.suspicious.withOpacity(0.3) : AppColors.border),
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text(
                      '${t['product']?['name'] ?? 'Product'} – ${t['quantity_sent']} ${t['unit']}',
                      style: const TextStyle(color: AppColors.textPrimary,
                          fontWeight: FontWeight.w600),
                    )),
                    StatusBadge(status: t['status'] ?? 'pending'),
                  ]),
                  const SizedBox(height: 6),
                  Text('${t['from_location'] ?? '?'} → ${t['to_location'] ?? '?'}',
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                  if (t['is_suspicious'] == true)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: SuspiciousBanner(reason: t['suspicious_reason'] ?? 'Flagged'),
                    ),
                  if (t['block_hash'] != null) ...[
                    const SizedBox(height: 4),
                    Text('⛓ ${t['block_hash'].toString().substring(0, 20)}...',
                        style: const TextStyle(color: AppColors.primary,
                            fontSize: 10, fontFamily: 'monospace')),
                  ],
                ]),
              );
            },
          );
  }

  // ── Blockchain tab ─────────────────────────────────────────
  Widget _buildBlockchain() {
    return const _BlockchainExplorer();
  }
}

class _BlockchainExplorer extends StatefulWidget {
  const _BlockchainExplorer();
  @override
  State<_BlockchainExplorer> createState() => _BlockchainExplorerState();
}

class _BlockchainExplorerState extends State<_BlockchainExplorer> {
  List _chain = [];
  Map? _stats;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    final [chainRes, statsRes] = await Future.wait([
      ApiService.getChain(),
      ApiService.getChainStats(),
    ]);
    if (mounted) setState(() {
      if (chainRes.success) _chain = chainRes.data['chain'] ?? [];
      if (statsRes.success) _stats = statsRes.data;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator(color: AppColors.primary));
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Chain stats
        if (_stats != null)
          Row(children: [
            Expanded(child: StatCard(
              title: 'Total Blocks', value: '${_stats!['total_blocks']}',
              icon: Icons.link_rounded, color: AppColors.primary)),
            const SizedBox(width: 10),
            Expanded(child: StatCard(
              title: 'Transactions', value: '${_stats!['total_transfers']}',
              icon: Icons.receipt_rounded, color: AppColors.inTransit)),
          ]),
        const SizedBox(height: 16),

        // Valid/invalid indicator
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.accent.withOpacity(0.1),
            borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.accent.withOpacity(0.3)),
          ),
          child: const Row(children: [
            Icon(Icons.verified_rounded, color: AppColors.accent),
            SizedBox(width: 10),
            Text('Chain Integrity: VALID',
                style: TextStyle(color: AppColors.accent, fontWeight: FontWeight.w700)),
          ]),
        ),
        const SizedBox(height: 16),

        const SectionHeader(title: 'Blockchain Explorer'),
        const SizedBox(height: 10),

        if (_chain.isEmpty)
          EmptyState(message: 'No blocks yet', icon: Icons.link_off_rounded)
        else
          ..._chain.asMap().map((i, b) => MapEntry(i,
            BlockCard(block: b, isLast: i == _chain.length - 1))).values,
      ]),
    );
  }
}
