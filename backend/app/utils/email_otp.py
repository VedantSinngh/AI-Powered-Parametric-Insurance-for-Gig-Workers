"""
GridGuard AI — Email OTP Utility
Async SMTP email sender using aiosmtplib with branded HTML template
"""

import hashlib
import hmac
import random
import secrets
import string

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def _otp_digest(otp: str, salt: str) -> str:
    payload = f"{salt}:{otp}:{settings.SECRET_KEY}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_otp(otp: str) -> str:
    """Hash OTP with salted SHA-256.

    OTPs are short-lived and verified server-side, so a fast hash with
    per-token salt + secret pepper keeps verification reliable in Docker
    builds where passlib/bcrypt backends can fail at runtime.
    """
    salt = secrets.token_hex(16)
    digest = _otp_digest(otp, salt)
    return f"{salt}${digest}"


def verify_otp(otp: str, otp_hash: str) -> bool:
    """Verify OTP against salted SHA-256 hash using constant-time compare."""
    if not otp_hash or "$" not in otp_hash:
        return False

    salt, expected_digest = otp_hash.split("$", 1)
    actual_digest = _otp_digest(otp, salt)
    return hmac.compare_digest(actual_digest, expected_digest)


def _build_otp_html(otp: str, partner_name: str = "Partner") -> str:
    """Build branded navy+amber HTML email template with OTP."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background-color:#0f1729; font-family:'Segoe UI',Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f1729; padding:40px 20px;">
            <tr>
                <td align="center">
                    <table width="480" cellpadding="0" cellspacing="0" style="background-color:#1a2332; border-radius:16px; overflow:hidden; box-shadow:0 8px 32px rgba(0,0,0,0.4);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #f59e0b, #d97706); padding:32px; text-align:center;">
                                <h1 style="margin:0; color:#0f1729; font-size:28px; font-weight:800; letter-spacing:-0.5px;">
                                    🛡️ GridGuard AI
                                </h1>
                                <p style="margin:8px 0 0; color:#0f1729; font-size:14px; opacity:0.8;">
                                    Parametric Income Protection
                                </p>
                            </td>
                        </tr>
                        <!-- Body -->
                        <tr>
                            <td style="padding:40px 32px;">
                                <p style="color:#94a3b8; font-size:16px; margin:0 0 8px;">
                                    Hi {partner_name},
                                </p>
                                <p style="color:#e2e8f0; font-size:16px; margin:0 0 32px; line-height:1.6;">
                                    Here's your one-time verification code to activate your GridGuard protection:
                                </p>
                                <!-- OTP Box -->
                                <div style="background-color:#0f1729; border:2px solid #f59e0b; border-radius:12px; padding:24px; text-align:center; margin:0 0 32px;">
                                    <span style="color:#f59e0b; font-size:36px; font-weight:800; letter-spacing:12px; font-family:'Courier New',monospace;">
                                        {otp}
                                    </span>
                                </div>
                                <p style="color:#64748b; font-size:13px; margin:0; line-height:1.5;">
                                    ⏱️ This code expires in <strong style="color:#f59e0b;">5 minutes</strong>.<br>
                                    🔒 Never share this code with anyone.
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="padding:20px 32px; border-top:1px solid #2d3748;">
                                <p style="color:#475569; font-size:12px; margin:0; text-align:center;">
                                    GridGuard AI — Protecting gig workers across India 🇮🇳
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


async def _send_email_with_fallback(msg: MIMEMultipart):
    """Send email with STARTTLS, then fall back to plain SMTP if unsupported."""
    username = settings.SMTP_USER or None
    password = settings.SMTP_PASSWORD or None

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=username,
            password=password,
            start_tls=True,
        )
        return True
    except Exception as first_error:
        if "STARTTLS extension not supported" not in str(first_error):
            raise

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=username,
            password=password,
            start_tls=False,
        )
        return True


async def send_otp_email(email: str, otp: str, partner_name: str = "Partner"):
    """Send OTP email via async SMTP (Gmail)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = email
    msg["Subject"] = "GridGuard AI — Your Protection Code"

    html_body = _build_otp_html(otp, partner_name)
    msg.attach(MIMEText(html_body, "html"))

    try:
        await _send_email_with_fallback(msg)
        return True
    except Exception as e:
        print(f"⚠️  Email send failed: {e}")
        return False


async def send_notification_email(
    email: str,
    subject: str,
    body_html: str,
):
    """Send a generic notification email."""
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        await _send_email_with_fallback(msg)
        return True
    except Exception as e:
        print(f"⚠️  Email send failed: {e}")
        return False
