// lib/screens/farmer/transfer_screen.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class TransferScreen extends StatefulWidget {
  final String productId;
  const TransferScreen({super.key, required this.productId});
  @override
  State<TransferScreen> createState() => _TransferScreenState();
}

class _TransferScreenState extends State<TransferScreen> {
  final _form = GlobalKey<FormState>();
  final _emailCtrl    = TextEditingController();
  final _locationCtrl = TextEditingController();
  final _qtyCtrl      = TextEditingController();
  final _noteCtrl     = TextEditingController();

  String _transferType = 'transfer';
  bool _loading = false;
  bool _success = false;
  String? _error;
  Map? _product;

  final _types = {
    'transfer': 'Direct Transfer',
    'collection': 'Collection Center',
    'warehouse': 'Warehouse',
    'final_delivery': 'Final Delivery',
  };

  @override
  void initState() { super.initState(); _loadProduct(); }

  Future<void> _loadProduct() async {
    final res = await ApiService.getProduct(widget.productId);
    if (res.success && mounted) {
      setState(() {
        _product = res.data['product'];
        _qtyCtrl.text = '${_product!['quantity']}';
      });
    }
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });

    final res = await ApiService.createTransfer({
      'product_id': widget.productId,
      'receiver_email': _emailCtrl.text.trim(),
      'to_location': _locationCtrl.text.trim(),
      'quantity_sent': double.parse(_qtyCtrl.text),
      'unit': _product?['unit'] ?? 'kg',
      'transfer_type': _transferType,
      'note': _noteCtrl.text.trim(),
    });

    setState(() {
      _loading = false;
      if (res.success) _success = true;
      else _error = res.errorMessage;
    });
  }

  @override
  void dispose() {
    for (final c in [_emailCtrl, _locationCtrl, _qtyCtrl, _noteCtrl]) c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Transfer Product')),
      body: LoadingOverlay(
        isLoading: _loading,
        child: _success ? _buildSuccess() : _buildForm(),
      ),
    );
  }

  Widget _buildForm() {
    if (_product == null) return const Center(
        child: CircularProgressIndicator(color: AppColors.primary));

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Form(
        key: _form,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // Product summary
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.cardBg, borderRadius: AppRadius.card,
              border: Border.all(color: AppColors.border)),
            child: Row(children: [
              const Icon(Icons.eco_rounded, color: AppColors.primary, size: 36),
              const SizedBox(width: 12),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_product!['name'] ?? '', style: const TextStyle(
                  color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 16)),
                Text('${_product!['batch_number']} • ${_product!['quantity']} ${_product!['unit']}',
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                Text('📍 ${_product!['current_location'] ?? 'Unknown'}',
                    style: const TextStyle(color: AppColors.primary, fontSize: 12)),
              ]),
            ]),
          ),
          const SizedBox(height: AppSpacing.lg),

          if (_error != null)
            Container(
              margin: const EdgeInsets.only(bottom: AppSpacing.md),
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.1), borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.error.withOpacity(0.3))),
              child: Text(_error!, style: const TextStyle(color: AppColors.error)),
            ),

          // Transfer type
          const Text('Transfer Type', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: _types.entries.map((e) {
            final selected = _transferType == e.key;
            return GestureDetector(
              onTap: () => setState(() => _transferType = e.key),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: selected ? AppColors.primary.withOpacity(0.15) : AppColors.cardBg,
                  borderRadius: AppRadius.card,
                  border: Border.all(color: selected ? AppColors.primary : AppColors.border,
                      width: selected ? 2 : 1),
                ),
                child: Text(e.value, style: TextStyle(
                  color: selected ? AppColors.primary : AppColors.textSecondary,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.normal,
                  fontSize: 13)),
              ),
            );
          }).toList()),
          const SizedBox(height: AppSpacing.md),

          AppTextField(
            label: 'Receiver Email *',
            hint: 'receiver@example.com',
            controller: _emailCtrl,
            keyboardType: TextInputType.emailAddress,
            prefixIcon: const Icon(Icons.email_outlined, color: AppColors.primary),
            validator: (v) => (v == null || !v.contains('@')) ? 'Valid email required' : null,
          ),
          const SizedBox(height: AppSpacing.md),

          AppTextField(
            label: 'Destination Location *',
            hint: 'e.g. Kampala Warehouse, Fort Portal Store',
            controller: _locationCtrl,
            prefixIcon: const Icon(Icons.location_on_outlined, color: AppColors.primary),
            validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: AppSpacing.md),

          AppTextField(
            label: 'Quantity to Transfer *',
            controller: _qtyCtrl,
            keyboardType: TextInputType.number,
            prefixIcon: const Icon(Icons.scale_rounded, color: AppColors.primary),
            validator: (v) {
              if (v == null || v.isEmpty) return 'Required';
              final qty = double.tryParse(v);
              if (qty == null || qty <= 0) return 'Invalid quantity';
              if (qty > (_product?['quantity'] ?? 0)) return 'Exceeds available quantity';
              return null;
            },
          ),
          const SizedBox(height: AppSpacing.md),

          AppTextField(
            label: 'Note (optional)',
            controller: _noteCtrl,
            maxLines: 3,
            prefixIcon: const Icon(Icons.notes_rounded, color: AppColors.primary),
          ),
          const SizedBox(height: AppSpacing.xl),

          SizedBox(
            width: double.infinity, height: 52,
            child: ElevatedButton.icon(
              onPressed: _loading ? null : _submit,
              icon: const Icon(Icons.send_rounded),
              label: const Text('Initiate Transfer'),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _buildSuccess() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.local_shipping_rounded, color: AppColors.inTransit, size: 72),
          const SizedBox(height: 16),
          const Text('Transfer Initiated!', style: TextStyle(
            color: AppColors.textPrimary, fontSize: 22, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text('Product is now in transit to ${_locationCtrl.text}',
              style: const TextStyle(color: AppColors.textSecondary),
              textAlign: TextAlign.center),
          const SizedBox(height: 8),
          const Text('A blockchain block has been recorded.',
              style: TextStyle(color: AppColors.primary, fontSize: 13)),
          const SizedBox(height: 30),
          ElevatedButton(
            onPressed: () => context.go('/farmer'),
            child: const Text('Back to Dashboard'),
          ),
        ]),
      ),
    );
  }
}
