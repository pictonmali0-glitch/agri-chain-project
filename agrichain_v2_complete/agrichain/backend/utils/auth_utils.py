"""Authentication utilities: OTP generation, email sending."""

import random
import string
from datetime import datetime, timedelta
from flask_mail import Message
from app import mail, db
from models.user import OTPCode


def generate_otp(length=6) -> str:
    """Generate a numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(email: str, code: str, purpose: str) -> bool:
    """Send OTP via email. Returns True on success."""
    subject_map = {
        'registration': 'AgriChain – Verify Your Email',
        'login': 'AgriChain – Login OTP',
        'reset': 'AgriChain – Password Reset OTP',
        'verification': 'AgriChain – Email Verification',
    }
    subject = subject_map.get(purpose, 'AgriChain – OTP Code')

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;background:#0a1a0a;color:#e0e0e0;padding:32px;border-radius:12px;border:1px solid #2a5a2a;">
      <div style="text-align:center;margin-bottom:24px;">
        <h1 style="color:#4caf50;font-size:28px;margin:0;">🌿 AgriChain</h1>
        <p style="color:#81c784;font-size:13px;margin:4px 0;">Agricultural Blockchain Supply Chain</p>
      </div>
      <h2 style="color:#a5d6a7;font-size:18px;">Your Verification Code</h2>
      <p style="color:#bdbdbd;">Use the code below to complete your {purpose.replace('_',' ')}:</p>
      <div style="background:#1a2e1a;border:2px solid #4caf50;border-radius:8px;padding:20px;text-align:center;margin:20px 0;">
        <span style="font-size:40px;font-weight:bold;letter-spacing:12px;color:#69f0ae;font-family:monospace;">{code}</span>
      </div>
      <p style="color:#9e9e9e;font-size:13px;">⏱ This code expires in <strong style="color:#ff9800;">5 minutes</strong>.</p>
      <p style="color:#9e9e9e;font-size:13px;">If you did not request this, please ignore this email.</p>
      <hr style="border-color:#2a5a2a;margin:24px 0;">
      <p style="color:#616161;font-size:11px;text-align:center;">AgriChain © 2024 – Kasese District, Uganda</p>
    </div>
    """

    try:
        msg = Message(subject=subject, recipients=[email], html=html_body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[MAIL ERROR] {e}")
        # In dev mode: print code to console
        print(f"[DEV OTP] {email} → {code} ({purpose})")
        return False  # Don't fail hard in development


def create_otp_record(email: str, purpose: str) -> str:
    """Invalidate old OTPs for this email+purpose, create new one."""
    # Expire old codes
    old = OTPCode.query.filter_by(email=email, purpose=purpose, is_used=False).all()
    for o in old:
        o.is_used = True
    db.session.flush()

    code = generate_otp()
    otp = OTPCode(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.session.add(otp)
    db.session.flush()
    return code


def verify_otp_code(email: str, code: str, purpose: str) -> tuple[bool, str]:
    """Verify an OTP. Returns (success, message)."""
    otp = OTPCode.query.filter_by(
        email=email, code=code, purpose=purpose, is_used=False
    ).order_by(OTPCode.created_at.desc()).first()

    if not otp:
        return False, "Invalid OTP code."

    otp.attempts += 1

    if not otp.is_valid():
        if datetime.utcnow() >= otp.expires_at:
            return False, "OTP has expired."
        if otp.attempts >= 5:
            return False, "Too many failed attempts. Request a new code."
        return False, "Invalid OTP."

    otp.is_used = True
    db.session.flush()
    return True, "OTP verified successfully."
