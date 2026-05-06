"""QR code generation and image utilities."""

import qrcode
import os
import json
from io import BytesIO
from PIL import Image
import base64


UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')


def generate_product_qr(product_id: str, batch_number: str) -> str:
    """
    Generate a QR code for a product.
    Returns the relative file path.
    """
    qr_dir = os.path.join(UPLOAD_FOLDER, 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)

    payload = json.dumps({
        "type": "AGRICHAIN_PRODUCT",
        "product_id": product_id,
        "batch": batch_number,
        "verify_url": f"https://agrichain.app/verify/{product_id}",
    })

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1b5e20", back_color="white")

    filename = f"qr_{product_id}.png"
    filepath = os.path.join(qr_dir, filename)
    img.save(filepath)

    return f"uploads/qrcodes/{filename}"


def get_qr_base64(product_id: str) -> str | None:
    """Return base64-encoded QR image for embedding in API response."""
    path = os.path.join(UPLOAD_FOLDER, 'qrcodes', f"qr_{product_id}.png")
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def save_uploaded_image(file_storage, subfolder: str = 'products') -> str:
    """Save an uploaded image file and return its relative path."""
    import uuid
    img_dir = os.path.join(UPLOAD_FOLDER, subfolder)
    os.makedirs(img_dir, exist_ok=True)

    ext = os.path.splitext(file_storage.filename)[1].lower() or '.jpg'
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(img_dir, filename)

    # Resize to max 1024x1024 to save space
    img = Image.open(file_storage.stream)
    img.thumbnail((1024, 1024), Image.LANCZOS)
    img.save(filepath)

    return f"uploads/{subfolder}/{filename}"


def generate_batch_number(category: str = '') -> str:
    """Generate a unique batch number like MAIZE-001-2024."""
    import random
    from datetime import datetime
    prefix = (category[:5].upper() if category else 'PROD')
    year = datetime.now().year
    rand = random.randint(1000, 9999)
    return f"{prefix}-{rand}-{year}"
