"""
GridGuard AI — Notification Service
Firebase FCM push + email notifications
"""

import json

import httpx

from app.config import settings
from app.utils.email_otp import send_notification_email


class NotificationService:
    """Handles push notifications (FCM) and email notifications."""

    async def send_fcm_push(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """Send push notification via Firebase Cloud Messaging."""
        if not settings.FIREBASE_SERVER_KEY or settings.FIREBASE_SERVER_KEY == "your-firebase-server-key":
            print("⚠️  FCM not configured, skipping push notification")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://fcm.googleapis.com/fcm/send",
                    json={
                        "to": device_token,
                        "notification": {
                            "title": title,
                            "body": body,
                            "sound": "default",
                        },
                        "data": data or {},
                    },
                    headers={
                        "Authorization": f"key={settings.FIREBASE_SERVER_KEY}",
                        "Content-Type": "application/json",
                    },
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            print(f"⚠️  FCM push failed: {e}")
            return False

    async def send_payout_notification(
        self,
        email: str,
        partner_name: str,
        amount: float,
        event_type: str,
        h3_cell: str,
        reference: str,
    ) -> bool:
        """Send payout credited email notification."""
        html = f"""
        <div style="font-family:Arial; padding:20px; background:#0f1729; color:#e2e8f0;">
            <h2 style="color:#f59e0b;">🛡️ GridGuard AI — Payout Credited!</h2>
            <p>Hi {partner_name},</p>
            <p>Great news! Your claim has been processed:</p>
            <table style="border-collapse:collapse; margin:20px 0;">
                <tr><td style="padding:8px; color:#94a3b8;">Amount:</td>
                    <td style="padding:8px; color:#22c55e; font-weight:bold;">₹{amount:.0f}</td></tr>
                <tr><td style="padding:8px; color:#94a3b8;">Event:</td>
                    <td style="padding:8px;">{event_type.replace('_',' ').title()}</td></tr>
                <tr><td style="padding:8px; color:#94a3b8;">Zone:</td>
                    <td style="padding:8px; font-family:monospace;">{h3_cell[:12]}...</td></tr>
                <tr><td style="padding:8px; color:#94a3b8;">Reference:</td>
                    <td style="padding:8px; font-family:monospace;">{reference}</td></tr>
            </table>
            <p style="color:#64748b; font-size:13px;">
                Your protection is always active. Stay safe! 🇮🇳
            </p>
        </div>
        """
        return await send_notification_email(
            email,
            f"GridGuard AI — ₹{amount:.0f} Payout Credited!",
            html,
        )

    async def send_premium_notification(
        self,
        email: str,
        partner_name: str,
        amount: float,
        week: str,
    ) -> bool:
        """Send premium deducted email."""
        html = f"""
        <div style="font-family:Arial; padding:20px; background:#0f1729; color:#e2e8f0;">
            <h2 style="color:#f59e0b;">🛡️ GridGuard AI — Weekly Premium</h2>
            <p>Hi {partner_name},</p>
            <p>Your weekly protection premium of <strong style="color:#f59e0b;">₹{amount:.0f}</strong>
               has been deducted for the week of {week}.</p>
            <p>You're now covered against climate disruptions! 🌧️☀️</p>
            <p style="color:#64748b; font-size:13px;">Stay safe out there! 🇮🇳</p>
        </div>
        """
        return await send_notification_email(
            email,
            f"GridGuard AI — ₹{amount:.0f} Weekly Premium Deducted",
            html,
        )


notification_service = NotificationService()
