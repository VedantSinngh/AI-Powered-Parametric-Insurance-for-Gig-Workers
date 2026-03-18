"""
GridGuard AI — Notification Service
Firebase Cloud Messaging (push) + Twilio (SMS) integration.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_push_notification(
    partner_id: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """
    Send a push notification via Firebase Cloud Messaging (FCM).
    In production, the partner_id would map to a device FCM token
    stored during onboarding.
    """
    try:
        if not settings.firebase_server_key:
            logger.warning("Firebase server key not configured; skipping push notification")
            return False

        # In production: look up FCM token for this partner
        # For now, using partner_id as a placeholder topic
        fcm_url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Authorization": f"key={settings.firebase_server_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": f"/topics/partner_{partner_id}",
            "notification": {
                "title": title,
                "body": body,
                "sound": "default",
            },
            "data": data or {},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(fcm_url, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info(f"Push notification sent to partner {partner_id}")
                return True
            else:
                logger.error(
                    f"FCM error {response.status_code}: {response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"Push notification failed for {partner_id}: {e}")
        return False


async def send_sms(to: str, message: str) -> bool:
    """
    Send SMS via Twilio.
    """
    try:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            logger.warning("Twilio credentials not configured; skipping SMS")
            return False

        twilio_url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.twilio_account_sid}/Messages.json"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                twilio_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data={
                    "To": to,
                    "From": settings.twilio_from_number,
                    "Body": message,
                },
            )

            if response.status_code in (200, 201):
                result = response.json()
                logger.info(f"SMS sent to {to}: SID={result.get('sid')}")
                return True
            else:
                logger.error(f"Twilio error {response.status_code}: {response.text}")
                return False

    except Exception as e:
        logger.error(f"SMS failed to {to}: {e}")
        return False


async def send_premium_notification(
    partner_id: str,
    phone_number: str | None,
    premium_amount: float,
    week_label: str,
) -> None:
    """Send premium deduction notification via push + SMS."""
    push_body = f"Your GridGuard cover for {week_label}: ₹{premium_amount}/week"
    await send_push_notification(
        partner_id=partner_id,
        title="Weekly Cover Active 🛡️",
        body=push_body,
    )

    if phone_number:
        await send_sms(
            to=phone_number,
            message=f"GridGuard: {push_body}. Premium will be deducted Monday 6AM.",
        )
