// lib/screens/farmer/add_product_screen.dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../services/api_service.dart';
import '../../utils/constants.dart';
import '../../widgets/common_widgets.dart';

class AddProductScreen extends StatefulWidget {
  const AddProductScreen({super.key});
  @override
  State<AddProductScreen> createState() => _AddProductScreenState();
}

class _AddProductScreenState extends State<AddProductScreen> {
  final _form = GlobalKey<FormState>();
  final _nameCtrl     = TextEditingController();
  final _categoryCtrl = TextEditingController();
  final _qtyCtrl      = TextEditingController();
  final _originCtrl   = TextEditingController();
  final _descCtrl     = TextEditingController();

  String _unit = 'kg';
  DateTime? _harvestDate;
  List<File> _images = [];
  bool _loading = false;
  Map? _createdProduct;
  String? _error;

  final _categories = ['Maize', 'Coffee', 'Beans', 'Rice', 'Cassava',
    'Bananas', 'Tomatoes', 'Other'];
  final _units = ['kg', 'tonnes', 'bags', 'litres', 'pieces'];

  Future<void> _pickImages() async {
    final picker = ImagePicker();
    final picked = await picker.pickMultiImage(imageQuality: 80);
    if (picked.isNotEmpty) {
      setState(() => _images = picked.map((x) => File(x.path)).toList());
    }
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
      builder: (context, child) => Theme(
        data: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(primary: AppColors.primary),
        ),
        child: child!,
      ),
    );
    if (d != null) setState(() => _harvestDate = d);
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; });

    final body = {
      'name': _nameCtrl.text.trim(),
      'category': _categoryCtrl.text.trim(),
      'quantity': double.parse(_qtyCtrl.text.trim()),
      'unit': _unit,
      'origin': _originCtrl.text.trim(),
      'description': _descCtrl.text.trim(),
      if (_harvestDate != null)
        'harvest_date': _harvestDate!.toIso8601String().substring(0, 10),
    };

    final res = await ApiService.createProduct(body);

    if (res.success) {
      final product = res.data['product'] as Map<String, dynamic>;
      // Upload images
      for (final img in _images) {
        await ApiService.uploadProductImages(product['id'], img);
      }
      setState(() { _createdProduct = product; _loading = false; });
    } else {
      setState(() { _error = res.errorMessage; _loading = false; });
    }
  }

  @override
  void dispose() {
    for (final c in [_nameCtrl, _categoryCtrl, _qtyCtrl, _originCtrl, _descCtrl]) c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Add Product')),
      body: LoadingOverlay(
        isLoading: _loading,
        child: _createdProduct != null ? _buildSuccess() : _buildForm(),
      ),
    );
  }

  Widget _buildForm() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Form(
        key: _form,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (_error != null)
            Container(
              margin: const EdgeInsets.only(bottom: AppSpacing.md),
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.1), borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.error.withOpacity(0.3)),
              ),
              child: Text(_error!, style: const TextStyle(color: AppColors.error)),
            ),

          AppTextField(
            label: 'Product Name *',
            hint: 'e.g. Maize, Coffee Beans',
            controller: _nameCtrl,
            prefixIcon: const Icon(Icons.eco_rounded, color: AppColors.primary),
            validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: AppSpacing.md),

          // Category dropdown
          DropdownButtonFormField<String>(
            value: _categoryCtrl.text.isEmpty ? null : _categoryCtrl.text,
            decoration: InputDecoration(
              labelText: 'Category',
              prefixIcon: const Icon(Icons.category_rounded, color: AppColors.primary),
              filled: true, fillColor: AppColors.surfaceLight,
              border: OutlineInputBorder(borderRadius: AppRadius.card,
                  borderSide: const BorderSide(color: AppColors.border)),
              enabledBorder: OutlineInputBorder(borderRadius: AppRadius.card,
                  borderSide: const BorderSide(color: AppColors.border)),
            ),
            dropdownColor: AppColors.surface,
            style: const TextStyle(color: AppColors.textPrimary),
            items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
            onChanged: (v) => _categoryCtrl.text = v ?? '',
          ),
          const SizedBox(height: AppSpacing.md),

          // Quantity + unit
          Row(children: [
            Expanded(
              child: AppTextField(
                label: 'Quantity *',
                controller: _qtyCtrl,
                keyboardType: TextInputType.number,
                prefixIcon: const Icon(Icons.scale_rounded, color: AppColors.primary),
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Required';
                  if (double.tryParse(v) == null) return 'Invalid number';
                  if (double.parse(v) <= 0) return 'Must be > 0';
                  return null;
                },
              ),
            ),
            const SizedBox(width: 10),
            DropdownButton<String>(
              value: _unit,
              dropdownColor: AppColors.surface,
              style: const TextStyle(color: AppColors.textPrimary),
              items: _units.map((u) => DropdownMenuItem(value: u, child: Text(u))).toList(),
              onChanged: (v) => setState(() => _unit = v ?? 'kg'),
            ),
          ]),
          const SizedBox(height: AppSpacing.md),

          AppTextField(
            label: 'Origin / Farm Location',
            hint: 'e.g. Kasese Farm, Western Uganda',
            controller: _originCtrl,
            prefixIcon: const Icon(Icons.location_on_outlined, color: AppColors.primary),
          ),
          const SizedBox(height: AppSpacing.md),

          // Harvest date
          GestureDetector(
            onTap: _pickDate,
            child: Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.surfaceLight, borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.border),
              ),
              child: Row(children: [
                const Icon(Icons.calendar_today_rounded, color: AppColors.primary),
                const SizedBox(width: 10),
                Text(
                  _harvestDate != null
                      ? 'Harvest: ${_harvestDate!.day}/${_harvestDate!.month}/${_harvestDate!.year}'
                      : 'Select Harvest Date (optional)',
                  style: TextStyle(
                    color: _harvestDate != null ? AppColors.textPrimary : AppColors.textSecondary),
                ),
              ]),
            ),
          ),
          const SizedBox(height: AppSpacing.md),

          AppTextField(
            label: 'Description (optional)',
            controller: _descCtrl,
            maxLines: 3,
            prefixIcon: const Icon(Icons.notes_rounded, color: AppColors.primary),
          ),
          const SizedBox(height: AppSpacing.md),

          // Image upload
          const Text('Product Images (optional)',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          const SizedBox(height: 8),
          GestureDetector(
            onTap: _pickImages,
            child: Container(
              height: 120,
              decoration: BoxDecoration(
                color: AppColors.surfaceLight, borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.border, style: BorderStyle.solid),
              ),
              child: _images.isEmpty
                  ? const Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Icon(Icons.add_photo_alternate_rounded, color: AppColors.primary, size: 36),
                      SizedBox(height: 8),
                      Text('Tap to upload images', style: TextStyle(color: AppColors.textSecondary)),
                    ]))
                  : ListView.builder(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.all(8),
                      itemCount: _images.length,
                      itemBuilder: (_, i) => Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.file(_images[i], width: 90, height: 100, fit: BoxFit.cover),
                        ),
                      ),
                    ),
            ),
          ),
          const SizedBox(height: AppSpacing.xl),

          SizedBox(
            width: double.infinity, height: 52,
            child: ElevatedButton.icon(
              onPressed: _loading ? null : _submit,
              icon: const Icon(Icons.add_rounded),
              label: const Text('Add Product & Generate QR'),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _buildSuccess() {
    final product = _createdProduct!;
    final batch = product['batch_number'] ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(children: [
        const Icon(Icons.check_circle_rounded, color: AppColors.accent, size: 72),
        const SizedBox(height: 16),
        const Text('Product Added!', style: TextStyle(
          color: AppColors.textPrimary, fontSize: 22, fontWeight: FontWeight.w700)),
        Text('Batch: $batch', style: const TextStyle(
          color: AppColors.primary, fontSize: 14, fontFamily: 'monospace')),
        const SizedBox(height: 30),

        // QR Code
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white, borderRadius: AppRadius.card),
          child: QrImageView(
            data: '{"product_id":"${product['id']}","batch":"$batch","type":"AGRICHAIN_PRODUCT"}',
            version: QrVersions.auto,
            size: 200,
            gapless: false,
          ),
        ),
        const SizedBox(height: 16),
        const Text('Scan this QR code to track the product',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
        const SizedBox(height: 30),

        // Product summary
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.cardBg, borderRadius: AppRadius.card,
            border: Border.all(color: AppColors.border)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _row('Name', product['name']),
            _row('Category', product['category'] ?? 'N/A'),
            _row('Quantity', '${product['quantity']} ${product['unit']}'),
            _row('Origin', product['origin'] ?? 'N/A'),
            _row('Status', product['status']),
          ]),
        ),
        const SizedBox(height: 24),

        Row(children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: () => context.go('/farmer/transfer/${product['id']}'),
              icon: const Icon(Icons.send_rounded, color: AppColors.primary),
              label: const Text('Transfer', style: TextStyle(color: AppColors.primary)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.primary),
                shape: RoundedRectangleBorder(borderRadius: AppRadius.card),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: () => context.go('/farmer'),
              icon: const Icon(Icons.dashboard_rounded),
              label: const Text('Dashboard'),
            ),
          ),
        ]),
      ]),
    );
  }

  Widget _row(String label, dynamic value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(children: [
      Text('$label: ', style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
      Text('${value ?? 'N/A'}', style: const TextStyle(color: AppColors.textPrimary, fontSize: 13)),
    ]),
  );
}
