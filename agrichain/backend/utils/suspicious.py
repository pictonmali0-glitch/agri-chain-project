"""Suspicious transaction detection for AgriChain."""

from datetime import datetime, timedelta
from models.blockchain import Transfer


def check_suspicious(transfer: Transfer, product) -> tuple[bool, str]:
    """
    Analyse a new transfer for suspicious patterns.
    Returns (is_suspicious, reason).
    """
    # Rule 1: Quantity anomaly – received > sent by > 5%
    if (transfer.quantity_received and
            transfer.quantity_received > transfer.quantity_sent * 1.05):
        return True, f"Quantity anomaly: sent {transfer.quantity_sent}, received {transfer.quantity_received}"

    # Rule 2: Impossible speed – same product transferred within 1 minute
    recent = Transfer.query.filter_by(product_id=transfer.product_id)\
        .filter(Transfer.created_at >= datetime.utcnow() - timedelta(minutes=1))\
        .filter(Transfer.id != transfer.id)\
        .count()
    if recent > 0:
        return True, "Duplicate rapid transfer detected within 60 seconds"

    # Rule 3: Transferred to same sender (self-transfer)
    if transfer.sender_id == transfer.receiver_id:
        return True, "Self-transfer detected (sender == receiver)"

    # Rule 4: Product status conflict – already acknowledged
    if product.status == 'acknowledged':
        return True, "Transfer attempted on already-acknowledged product"

    return False, ""


def flag_qr_abuse(product_id: str, user_id: str) -> tuple[bool, str]:
    """Check for QR code scanning abuse."""
    from datetime import datetime, timedelta
    from models.blockchain import Transfer

    recent_scans = Transfer.query.filter_by(
        product_id=product_id,
        receiver_id=user_id
    ).filter(
        Transfer.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).count()

    if recent_scans >= 5:
        return True, f"QR code scanned {recent_scans} times by same user in 1 hour"
    return False, ""
