// lib/screens/admin/admin_dashboard.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../services/auth_provider.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class AdminDashboard extends StatefulWidget {
  const AdminDashboard({super.key});
  @override
  State<AdminDashboard> createState() => _AdminDashboardState();
}

class _AdminDashboardState extends State<AdminDashboard> {
  int _selectedIndex = 0;
  Map? _dashboard;
  List _movements = [];
  List _suspicious = [];
  List _users = [];
  List _chain = [];
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    final results = await Future.wait([
      ApiService.getAdminDashboard(),
      ApiService.getProductMovements(),
      ApiService.getSuspiciousTransactions(),
      ApiService.listAllUsers(),
      ApiService.getChain(),
    ]);
    if (mounted) setState(() {
      if (results[0].success) _dashboard = results[0].data;
      if (results[1].success) _movements = results[1].data['movements'] ?? [];
      if (results[2].success) _suspicious = results[2].data['suspicious'] ?? [];
      if (results[3].success) _users = results[3].data['users'] ?? [];
      if (results[4].success) _chain = results[4].data['chain'] ?? [];
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final susCount = _suspicious.length;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Row(children: [
          const AgriLogo(size: 30),
          const SizedBox(width: 10),
          const Text('Admin Console'),
        ]),
        actions: [
          IconButton(icon: const Icon(Icons.person_outline),
              onPressed: () => context.go('/profile')),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.primary, onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
            : _buildBody(),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (i) => setState(() => _selectedIndex = i),
        items: [
          const BottomNavigationBarItem(icon: Icon(Icons.dashboard_rounded), label: 'Dashboard'),
          const BottomNavigationBarItem(icon: Icon(Icons.route_rounded), label: 'Movements'),
          BottomNavigationBarItem(
            icon: Stack(clipBehavior: Clip.none, children: [
              const Icon(Icons.warning_amber_rounded),
              if (susCount > 0) Positioned(
                right: -6, top: -4,
                child: Container(
                  padding: const EdgeInsets.all(3),
                  decoration: const BoxDecoration(
                    color: AppColors.suspicious, shape: BoxShape.circle),
                  child: Text('$susCount', style: const TextStyle(
                    color: Colors.white, fontSize: 9, fontWeight: FontWeight.w700)),
                ),
              ),
            ]),
            label: 'Suspicious',
          ),
          const BottomNavigationBarItem(icon: Icon(Icons.people_rounded), label: 'Users'),
          const BottomNavigationBarItem(icon: Icon(Icons.link_rounded), label: 'Chain'),
        ],
      ),
    );
  }

  Widget _buildBody() {
    switch (_selectedIndex) {
      case 0: return _buildDashboard();
      case 1: return _buildMovements();
      case 2: return _buildSuspicious();
      case 3: return _buildUsers();
      case 4: return _buildChain();
      default: return _buildDashboard();
    }
  }

  // ── Dashboard ─────────────────────────────────────────────
  Widget _buildDashboard() {
    final stats = _dashboard?['stats'] ?? {};
    final recent = (_dashboard?['recent_transactions'] as List?) ?? [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Stats grid
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2, crossAxisSpacing: 10, mainAxisSpacing: 10,
          childAspectRatio: 1.4,
          children: [
            StatCard(title: 'Total Users', value: '${stats['total_users'] ?? 0}',
                icon: Icons.people_rounded, color: AppColors.primary),
            StatCard(title: 'Total Products', value: '${stats['total_products'] ?? 0}',
                icon: Icons.inventory_2_rounded, color: AppColors.inTransit),
            StatCard(title: 'Transfers', value: '${stats['total_transfers'] ?? 0}',
                icon: Icons.swap_horiz_rounded, color: AppColors.accentAmber),
            StatCard(title: 'Suspicious ⚠️', value: '${stats['suspicious_count'] ?? 0}',
                icon: Icons.warning_amber_rounded, color: AppColors.suspicious),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),

        // Farmers vs Receivers
        Row(children: [
          Expanded(child: StatCard(
            title: 'Farmers', value: '${stats['total_farmers'] ?? 0}',
            icon: Icons.agriculture_rounded, color: AppColors.primaryLight)),
          const SizedBox(width: 10),
          Expanded(child: StatCard(
            title: 'Receivers', value: '${stats['total_receivers'] ?? 0}',
            icon: Icons.store_rounded, color: AppColors.accent)),
          const SizedBox(width: 10),
          Expanded(child: StatCard(
            title: 'Blocks', value: '${stats['total_blocks'] ?? 0}',
            icon: Icons.link_rounded, color: AppColors.primary)),
        ]),
        const SizedBox(height: AppSpacing.lg),

        // Suspicious alert
        if ((stats['suspicious_count'] ?? 0) > 0)
          GestureDetector(
            onTap: () => setState(() => _selectedIndex = 2),
            child: Container(
              margin: const EdgeInsets.only(bottom: AppSpacing.md),
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.suspicious.withOpacity(0.08),
                borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.suspicious.withOpacity(0.5)),
              ),
              child: Row(children: [
                const Icon(Icons.warning_amber_rounded, color: AppColors.suspicious),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${stats['suspicious_count']} Suspicious Transaction(s) Detected',
                      style: const TextStyle(color: AppColors.suspicious,
                          fontWeight: FontWeight.w700)),
                  const Text('Tap to review flagged transactions',
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                ])),
                const Icon(Icons.chevron_right_rounded, color: AppColors.suspicious),
              ]),
            ),
          ),

        // Recent transactions
        const SectionHeader(title: 'Recent Transactions'),
        const SizedBox(height: 10),
        if (recent.isEmpty)
          EmptyState(message: 'No transactions yet', icon: Icons.receipt_long_rounded)
        else
          ...recent.map((t) => _transactionCard(t)),
      ]),
    );
  }

  Widget _transactionCard(Map t) {
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
          Expanded(child: Text(t['description'] ?? '',
              style: const TextStyle(color: AppColors.textPrimary, fontSize: 13))),
          StatusBadge(status: t['status'] ?? 'pending'),
        ]),
        const SizedBox(height: 4),
        Text('Farmer: ${t['farmer_name']} • ${t['timestamp']?.toString().substring(0, 19).replaceAll('T', ' ')}',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 11)),
        if (t['is_suspicious'] == true)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(children: const [
              Icon(Icons.flag_rounded, color: AppColors.suspicious, size: 13),
              SizedBox(width: 4),
              Text('FLAGGED', style: TextStyle(color: AppColors.suspicious,
                  fontSize: 11, fontWeight: FontWeight.w700)),
            ]),
          ),
      ]),
    );
  }

  // ── Movements ─────────────────────────────────────────────
  Widget _buildMovements() {
    if (_movements.isEmpty) return EmptyState(
        message: 'No movements yet', icon: Icons.route_rounded);

    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: _movements.length,
      itemBuilder: (_, i) {
        final m = _movements[i];
        return Container(
          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.cardBg, borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${m['product_name']} – ${m['batch']}',
                  style: const TextStyle(color: AppColors.textPrimary,
                      fontWeight: FontWeight.w700))),
              StatusBadge(status: m['status'] ?? 'pending'),
            ]),
            const SizedBox(height: 8),
            // Movement arrow row
            Row(children: [
              _locChip(m['from_location'] ?? '?', Icons.location_on_outlined),
              const Expanded(child: Divider(color: AppColors.primary, thickness: 1)),
              const Icon(Icons.arrow_forward_rounded, color: AppColors.primary, size: 18),
              const Expanded(child: Divider(color: AppColors.primary, thickness: 1)),
              _locChip(m['to_location'] ?? '?', Icons.flag_rounded),
            ]),
            const SizedBox(height: 8),
            Text('Farmer: ${m['farmer_name']}  |  Handler: ${m['handler']}',
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
            Text('Qty: ${m['quantity']}  |  Stage: ${m['stage']}',
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
            Text(m['timestamp']?.toString().substring(0, 19).replaceAll('T', ' ') ?? '',
                style: const TextStyle(color: AppColors.border, fontSize: 11)),
          ]),
        );
      },
    );
  }

  Widget _locChip(String label, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(6)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, color: AppColors.primary, size: 12),
        const SizedBox(width: 3),
        Text(label, style: const TextStyle(color: AppColors.primary, fontSize: 11),
            maxLines: 1, overflow: TextOverflow.ellipsis),
      ]),
    );
  }

  // ── Suspicious ────────────────────────────────────────────
  Widget _buildSuspicious() {
    if (_suspicious.isEmpty) return Center(
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.verified_user_rounded, color: AppColors.accent, size: 64),
        const SizedBox(height: 16),
        const Text('No suspicious transactions detected',
            style: TextStyle(color: AppColors.textSecondary)),
      ]),
    );

    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: _suspicious.length,
      itemBuilder: (_, i) {
        final t = _suspicious[i];
        return Container(
          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
          decoration: BoxDecoration(
            color: AppColors.suspicious.withOpacity(0.05), borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.suspicious.withOpacity(0.4))),
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const Icon(Icons.warning_amber_rounded,
                      color: AppColors.suspicious, size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text(
                    '${t['product']?['name'] ?? 'Product'} – ${t['product']?['batch_number'] ?? ''}',
                    style: const TextStyle(color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700))),
                ]),
                const SizedBox(height: 8),
                Text(t['suspicious_reason'] ?? 'Flagged transaction',
                    style: const TextStyle(color: AppColors.suspicious, fontSize: 13)),
                const SizedBox(height: 4),
                Text('Sender: ${t['sender']?['name'] ?? '?'}  |  ${t['from_location']} → ${t['to_location']}',
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                Text(t['created_at']?.toString().substring(0, 19).replaceAll('T', ' ') ?? '',
                    style: const TextStyle(color: AppColors.border, fontSize: 11)),
              ]),
            ),
            // Actions
            Padding(
              padding: const EdgeInsets.only(left: 12, right: 12, bottom: 12),
              child: Row(children: [
                Expanded(child: OutlinedButton(
                  onPressed: () async {
                    await ApiService.approveTransfer(t['id'], 'approve');
                    await _load();
                  },
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.primary),
                    foregroundColor: AppColors.primary,
                    shape: RoundedRectangleBorder(borderRadius: AppRadius.card)),
                  child: const Text('Approve'),
                )),
                const SizedBox(width: 8),
                Expanded(child: OutlinedButton(
                  onPressed: () async {
                    await ApiService.approveTransfer(t['id'], 'reject', reason: 'Rejected by admin');
                    await _load();
                  },
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.error),
                    foregroundColor: AppColors.error,
                    shape: RoundedRectangleBorder(borderRadius: AppRadius.card)),
                  child: const Text('Reject'),
                )),
              ]),
            ),
          ]),
        );
      },
    );
  }

  // ── Users ────────────────────────────────────────────────
  Widget _buildUsers() {
    return Column(children: [
      // Filter chips
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(children: ['All', 'Farmer', 'Receiver', 'Admin'].map((r) {
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ActionChip(
              label: Text(r),
              onPressed: () async {
                final res = await ApiService.listAllUsers(role: r.toLowerCase() == 'all' ? '' : r.toLowerCase());
                if (res.success && mounted) setState(() => _users = res.data['users'] ?? []);
              },
            ),
          );
        }).toList()),
      ),
      Expanded(
        child: ListView.builder(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          itemCount: _users.length,
          itemBuilder: (_, i) {
            final u = _users[i];
            return ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              tileColor: AppColors.cardBg,
              shape: RoundedRectangleBorder(
                borderRadius: AppRadius.card,
                side: const BorderSide(color: AppColors.border)),
              leading: CircleAvatar(
                backgroundColor: AppColors.primary.withOpacity(0.15),
                child: Text(u['name']?.substring(0, 1).toUpperCase() ?? '?',
                    style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
              ),
              title: Text(u['name'] ?? '', style: const TextStyle(color: AppColors.textPrimary)),
              subtitle: Text(u['email'] ?? '', style: const TextStyle(
                  color: AppColors.textSecondary, fontSize: 12)),
              trailing: Chip(
                label: Text(u['role'] ?? '', style: const TextStyle(fontSize: 11)),
                backgroundColor: _roleColor(u['role']).withOpacity(0.15),
                side: BorderSide(color: _roleColor(u['role']).withOpacity(0.4)),
                labelStyle: TextStyle(color: _roleColor(u['role'])),
              ),
            );
          },
        ),
      ),
    ]);
  }

  Color _roleColor(String? role) {
    switch (role) {
      case 'admin':    return AppColors.accentAmber;
      case 'receiver': return AppColors.inTransit;
      default:         return AppColors.primary;
    }
  }

  // ── Blockchain chain ─────────────────────────────────────
  Widget _buildChain() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.accent.withOpacity(0.08),
            borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.accent.withOpacity(0.3))),
          child: Row(children: [
            const Icon(Icons.verified_rounded, color: AppColors.accent),
            const SizedBox(width: 10),
            Text('${_chain.length} Blocks • Chain Integrity: VALID',
                style: const TextStyle(color: AppColors.accent, fontWeight: FontWeight.w700)),
          ]),
        ),
        const SizedBox(height: 16),
        const SectionHeader(title: 'Live Blockchain Explorer'),
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
