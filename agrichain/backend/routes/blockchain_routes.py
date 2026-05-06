"""Blockchain explorer routes."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models.blockchain import BlockchainBlock, Transfer
from app import db

blockchain_bp = Blueprint('blockchain', __name__)


# ── Full chain ─────────────────────────────────────────────────
@blockchain_bp.route('/chain', methods=['GET'])
@jwt_required()
def get_chain():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = BlockchainBlock.query\
        .order_by(BlockchainBlock.block_index.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    blocks = [b.to_dict() for b in pagination.items]

    return jsonify({
        'chain': blocks,
        'total_blocks': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'chain_valid': _verify_chain_integrity(),
    }), 200


# ── Verify chain integrity ─────────────────────────────────────
@blockchain_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_chain():
    valid = _verify_chain_integrity()
    blocks = BlockchainBlock.query.order_by(BlockchainBlock.block_index.asc()).all()
    issues = []

    for i, block in enumerate(blocks):
        if not block.verify_integrity():
            issues.append({'block_index': block.block_index, 'issue': 'Hash mismatch'})
        if i > 0 and block.previous_hash != blocks[i-1].current_hash:
            issues.append({
                'block_index': block.block_index,
                'issue': 'Previous hash chain broken'
            })

    return jsonify({
        'chain_valid': valid,
        'total_blocks': len(blocks),
        'issues': issues,
    }), 200


# ── Single block ───────────────────────────────────────────────
@blockchain_bp.route('/block/<int:block_index>', methods=['GET'])
@jwt_required()
def get_block(block_index):
    block = BlockchainBlock.query.filter_by(block_index=block_index).first_or_404()
    return jsonify({'block': block.to_dict()}), 200


# ── Product chain ──────────────────────────────────────────────
@blockchain_bp.route('/product/<product_id>', methods=['GET'])
@jwt_required()
def product_chain(product_id):
    """Get blockchain blocks related to a specific product."""
    transfers = Transfer.query.filter_by(product_id=product_id)\
        .order_by(Transfer.created_at.asc()).all()

    chain = []
    for t in transfers:
        block = BlockchainBlock.query.filter_by(transaction_id=t.id).first()
        if block:
            chain.append({
                'block': block.to_dict(),
                'transfer': t.to_dict(),
            })

    return jsonify({
        'product_id': product_id,
        'chain': chain,
        'valid': all(b['block']['is_valid'] for b in chain) if chain else True,
    }), 200


# ── Stats ──────────────────────────────────────────────────────
@blockchain_bp.route('/stats', methods=['GET'])
@jwt_required()
def chain_stats():
    total_blocks = BlockchainBlock.query.count()
    total_transfers = Transfer.query.count()
    suspicious = Transfer.query.filter_by(is_suspicious=True).count()
    latest = BlockchainBlock.query.order_by(BlockchainBlock.block_index.desc()).first()

    return jsonify({
        'total_blocks': total_blocks,
        'total_transfers': total_transfers,
        'suspicious_count': suspicious,
        'latest_block': latest.to_dict() if latest else None,
    }), 200


def _verify_chain_integrity() -> bool:
    blocks = BlockchainBlock.query.order_by(BlockchainBlock.block_index.asc()).all()
    for i, block in enumerate(blocks):
        if not block.verify_integrity():
            return False
        if i > 0 and block.previous_hash != blocks[i-1].current_hash:
            return False
    return True
