// lib/widgets/common_widgets.dart
import 'package:flutter/material.dart';
import '../utils/constants.dart';

// ── AgriChain Logo ────────────────────────────────────────────
class AgriLogo extends StatelessWidget {
  final double size;
  const AgriLogo({super.key, this.size = 48});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primaryDark, AppColors.accent],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(size * 0.25),
        boxShadow: [BoxShadow(
          color: AppColors.primary.withOpacity(0.4),
          blurRadius: 12,
          offset: const Offset(0, 4),
        )],
      ),
      child: Icon(Icons.agriculture_rounded, color: Colors.black, size: size * 0.55),
    );
  }
}

// ── Section header ────────────────────────────────────────────
class SectionHeader extends StatelessWidget {
  final String title;
  final String? action;
  final VoidCallback? onAction;
  const SectionHeader({super.key, required this.title, this.action, this.onAction});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
        if (action != null)
          TextButton(
            onPressed: onAction,
            child: Text(action!, style: const TextStyle(
              color: AppColors.primary, fontSize: 13)),
          ),
      ],
    );
  }
}

// ── Status badge ──────────────────────────────────────────────
class StatusBadge extends StatelessWidget {
  final String status;
  const StatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final color = statusColor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(statusIcon(status), color: color, size: 12),
        const SizedBox(width: 4),
        Text(statusLabel(status),
            style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

// ── Info card ─────────────────────────────────────────────────
class InfoCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color? iconColor;
  final VoidCallback? onTap;
  const InfoCard({super.key, required this.label, required this.value,
    required this.icon, this.iconColor, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.cardBg,
          borderRadius: AppRadius.card,
          border: Border.all(color: AppColors.border),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: iconColor ?? AppColors.primary, size: 18),
            const SizedBox(width: 6),
            Text(label, style: const TextStyle(
              color: AppColors.textSecondary, fontSize: 12)),
          ]),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(
            color: AppColors.textPrimary, fontSize: 18, fontWeight: FontWeight.w700),
            maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      ),
    );
  }
}

// ── Stat card (dashboard) ─────────────────────────────────────
class StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  const StatCard({super.key, required this.title, required this.value,
    required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: AppRadius.card,
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: color, size: 20),
        ),
        const SizedBox(height: 12),
        Text(value, style: const TextStyle(
          color: AppColors.textPrimary, fontSize: 24, fontWeight: FontWeight.w800)),
        const SizedBox(height: 2),
        Text(title, style: const TextStyle(
          color: AppColors.textSecondary, fontSize: 12)),
      ]),
    );
  }
}

// ── Loading overlay ───────────────────────────────────────────
class LoadingOverlay extends StatelessWidget {
  final bool isLoading;
  final Widget child;
  const LoadingOverlay({super.key, required this.isLoading, required this.child});

  @override
  Widget build(BuildContext context) {
    return Stack(children: [
      child,
      if (isLoading)
        Container(
          color: Colors.black54,
          child: const Center(
            child: CircularProgressIndicator(color: AppColors.primary),
          ),
        ),
    ]);
  }
}

// ── Empty state ───────────────────────────────────────────────
class EmptyState extends StatelessWidget {
  final String message;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;
  const EmptyState({super.key, required this.message, required this.icon,
    this.actionLabel, this.onAction});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        Icon(icon, color: AppColors.border, size: 64),
        const SizedBox(height: 16),
        Text(message, style: const TextStyle(
          color: AppColors.textSecondary, fontSize: 15),
          textAlign: TextAlign.center),
        if (actionLabel != null) ...[
          const SizedBox(height: 20),
          ElevatedButton(onPressed: onAction, child: Text(actionLabel!)),
        ],
      ]),
    );
  }
}

// ── Suspicious banner ─────────────────────────────────────────
class SuspiciousBanner extends StatelessWidget {
  final String reason;
  const SuspiciousBanner({super.key, required this.reason});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.suspicious.withOpacity(0.1),
        borderRadius: AppRadius.card,
        border: Border.all(color: AppColors.suspicious.withOpacity(0.4)),
      ),
      child: Row(children: [
        const Icon(Icons.warning_amber_rounded, color: AppColors.suspicious, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Text(
          '⚠️ Suspicious: $reason',
          style: const TextStyle(color: AppColors.suspicious, fontSize: 13),
        )),
      ]),
    );
  }
}

// ── Block chain card ──────────────────────────────────────────
class BlockCard extends StatelessWidget {
  final Map<String, dynamic> block;
  final bool isLast;
  const BlockCard({super.key, required this.block, this.isLast = false});

  @override
  Widget build(BuildContext context) {
    final hash = block['current_hash']?.toString() ?? '';
    final shortHash = hash.length > 16 ? '${hash.substring(0, 8)}...${hash.substring(hash.length - 8)}' : hash;
    final isValid = block['is_valid'] as bool? ?? true;
    final isGenesis = block['is_genesis'] as bool? ?? false;

    return Column(children: [
      Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.cardBg,
          borderRadius: AppRadius.card,
          border: Border.all(
            color: isValid
                ? (isGenesis ? AppColors.accentAmber : AppColors.primary).withOpacity(0.4)
                : AppColors.error,
            width: 1.5,
          ),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: (isGenesis ? AppColors.accentAmber : AppColors.primary).withOpacity(0.15),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                isGenesis ? '⚡ GENESIS' : 'Block #${block['block_index']}',
                style: TextStyle(
                  color: isGenesis ? AppColors.accentAmber : AppColors.primary,
                  fontSize: 11, fontWeight: FontWeight.w700,
                  fontFamily: 'monospace',
                ),
              ),
            ),
            const Spacer(),
            Icon(
              isValid ? Icons.verified_rounded : Icons.error_rounded,
              color: isValid ? AppColors.primary : AppColors.error,
              size: 16,
            ),
            const SizedBox(width: 4),
            Text(isValid ? 'Valid' : 'TAMPERED',
                style: TextStyle(
                  color: isValid ? AppColors.primary : AppColors.error,
                  fontSize: 11, fontWeight: FontWeight.w600)),
          ]),
          const SizedBox(height: 10),
          _hashRow('Hash', shortHash, AppColors.accent),
          const SizedBox(height: 4),
          _hashRow('Prev', _shortHash(block['previous_hash']), AppColors.textSecondary),
          const SizedBox(height: 6),
          Text(
            block['timestamp']?.toString().substring(0, 19).replaceAll('T', ' ') ?? '',
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 11),
          ),
        ]),
      ),
      if (!isLast)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 4),
          child: Icon(Icons.arrow_downward_rounded, color: AppColors.primary, size: 18),
        ),
    ]);
  }

  String _shortHash(dynamic h) {
    final s = h?.toString() ?? '';
    return s.length > 12 ? '${s.substring(0, 6)}...${s.substring(s.length - 6)}' : s;
  }

  Widget _hashRow(String label, String value, Color color) {
    return Row(children: [
      Text('$label: ', style: const TextStyle(color: AppColors.textSecondary, fontSize: 11)),
      Text(value, style: TextStyle(color: color, fontSize: 11, fontFamily: 'monospace')),
    ]);
  }
}

// ── Timeline step ─────────────────────────────────────────────
class TimelineStep extends StatelessWidget {
  final Map<String, dynamic> step;
  final bool isFirst;
  final bool isLast;
  const TimelineStep({super.key, required this.step, this.isFirst = false, this.isLast = false});

  @override
  Widget build(BuildContext context) {
    final status = step['status']?.toString() ?? 'pending';
    final color = statusColor(status);

    return IntrinsicHeight(
      child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Column(children: [
          if (!isFirst) Container(width: 2, height: 12, color: AppColors.border),
          Container(
            width: 28, height: 28,
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              shape: BoxShape.circle,
              border: Border.all(color: color, width: 2),
            ),
            child: Icon(statusIcon(status), color: color, size: 14),
          ),
          if (!isLast) Expanded(child: Container(width: 2, color: AppColors.border)),
        ]),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: EdgeInsets.only(bottom: isLast ? 0 : AppSpacing.md, top: 4),
            child: Container(
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.cardBg,
                borderRadius: AppRadius.card,
                border: Border.all(color: AppColors.border),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text(
                    '${step['from'] ?? step['from_location'] ?? '?'} → ${step['to'] ?? step['to_location'] ?? '?'}',
                    style: const TextStyle(
                      color: AppColors.textPrimary, fontSize: 13, fontWeight: FontWeight.w600),
                  )),
                  StatusBadge(status: status),
                ]),
                const SizedBox(height: 6),
                Text('Handler: ${step['handler'] ?? step['handler_name'] ?? 'Unknown'}',
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                if (step['quantity'] != null || step['quantity_sent'] != null)
                  Text('Qty: ${step['quantity'] ?? '${step['quantity_sent']} ${step['unit']}'}',
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                const SizedBox(height: 4),
                Text(
                  _formatDate(step['timestamp'] ?? ''),
                  style: const TextStyle(color: AppColors.border, fontSize: 11),
                ),
                if (step['block_hash'] != null) ...[
                  const SizedBox(height: 4),
                  Text('⛓ ${step['block_hash'].toString().substring(0, 16)}...',
                    style: const TextStyle(color: AppColors.primary, fontSize: 10, fontFamily: 'monospace')),
                ],
              ]),
            ),
          ),
        ),
      ]),
    );
  }

  String _formatDate(String ts) {
    try {
      final dt = DateTime.parse(ts).toLocal();
      return '${dt.day}/${dt.month}/${dt.year} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return ts;
    }
  }
}

// ── App text field ────────────────────────────────────────────
class AppTextField extends StatelessWidget {
  final String label;
  final String? hint;
  final TextEditingController? controller;
  final bool obscureText;
  final TextInputType? keyboardType;
  final String? Function(String?)? validator;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final int? maxLines;
  final void Function(String)? onChanged;

  const AppTextField({
    super.key,
    required this.label,
    this.hint,
    this.controller,
    this.obscureText = false,
    this.keyboardType,
    this.validator,
    this.prefixIcon,
    this.suffixIcon,
    this.maxLines = 1,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      validator: validator,
      maxLines: maxLines,
      onChanged: onChanged,
      style: const TextStyle(color: AppColors.textPrimary, fontSize: 15),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: prefixIcon,
        suffixIcon: suffixIcon,
      ),
    );
  }
}
