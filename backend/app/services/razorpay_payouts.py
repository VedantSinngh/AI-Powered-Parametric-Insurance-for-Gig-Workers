"""
GridGuard AI — RazorpayX Payout Service
Supports test mode disbursements via RazorpayX APIs.
"""

from dataclasses import dataclass
from datetime import datetime
import base64
import hashlib
import hmac
from uuid import uuid4

import httpx

from app.config import settings
from app.models.partner import Partner


class RazorpayPayoutError(Exception):
    """Raised when Razorpay payout operations fail."""


@dataclass
class RazorpayPayoutResult:
    payout_id: str
    status: str
    reference: str


class RazorpayPayoutService:
    """RazorpayX payout integration with partner-scoped contact and fund accounts."""

    base_url = "https://api.razorpay.com"

    @staticmethod
    def is_enabled() -> bool:
        return all([
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
            settings.RAZORPAYX_ACCOUNT_NUMBER,
        ])

    @staticmethod
    def to_internal_status(provider_status: str | None) -> str:
        status = (provider_status or "").lower()
        if status == "processed":
            return "paid"
        if status in {"queued", "pending", "processing"}:
            return "processing"
        if status in {"failed", "reversed", "rejected", "cancelled"}:
            return "failed"
        return "processing"

    @staticmethod
    def verify_signature(payload: bytes, signature: str | None) -> bool:
        if not settings.RAZORPAY_WEBHOOK_SECRET or not signature:
            return False

        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def _auth_header() -> dict[str, str]:
        basic = base64.b64encode(
            f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode("utf-8")
        ).decode("ascii")
        return {"Authorization": f"Basic {basic}"}

    async def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = {
            **self._auth_header(),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.request(method, url, headers=headers, json=payload)

        if response.content:
            try:
                data = response.json()
            except ValueError:
                data = {}
        else:
            data = {}
        if response.status_code >= 400:
            error = data.get("error", {}) if isinstance(data, dict) else {}
            message = (
                error.get("description")
                or error.get("reason")
                or f"Razorpay API error ({response.status_code})"
            )
            raise RazorpayPayoutError(message)

        return data

    async def _ensure_contact(self, partner: Partner) -> str:
        if partner.razorpay_contact_id:
            return partner.razorpay_contact_id

        payload = {
            "name": partner.full_name,
            "email": partner.email,
            "type": "employee",
            "reference_id": partner.id,
            "notes": {
                "partner_id": partner.id,
                "city": partner.city,
            },
        }
        created = await self._request("POST", "/v1/contacts", payload)
        contact_id = created.get("id")
        if not contact_id:
            raise RazorpayPayoutError("Unable to create Razorpay contact")

        partner.razorpay_contact_id = contact_id
        partner.updated_at = datetime.utcnow()
        await partner.save()
        return contact_id

    async def _ensure_fund_account(self, partner: Partner, contact_id: str) -> str:
        if not partner.upi_handle:
            raise RazorpayPayoutError("Partner UPI handle missing")

        if partner.razorpay_fund_account_id:
            return partner.razorpay_fund_account_id

        payload = {
            "contact_id": contact_id,
            "account_type": "vpa",
            "vpa": {
                "address": partner.upi_handle,
            },
            "reference_id": partner.id,
        }
        created = await self._request("POST", "/v1/fund_accounts", payload)
        fund_account_id = created.get("id")
        if not fund_account_id:
            raise RazorpayPayoutError("Unable to create Razorpay fund account")

        partner.razorpay_fund_account_id = fund_account_id
        partner.updated_at = datetime.utcnow()
        await partner.save()
        return fund_account_id

    async def create_payout(self, partner: Partner, amount_inr: float, description: str) -> RazorpayPayoutResult:
        if not self.is_enabled():
            raise RazorpayPayoutError("Razorpay test mode is not fully configured")

        contact_id = await self._ensure_contact(partner)
        fund_account_id = await self._ensure_fund_account(partner, contact_id)

        amount_paise = int(round(amount_inr * 100))
        if amount_paise <= 0:
            raise RazorpayPayoutError("Payout amount must be positive")

        reference_id = f"gridguard-{uuid4().hex[:16]}"
        payload = {
            "account_number": settings.RAZORPAYX_ACCOUNT_NUMBER,
            "fund_account_id": fund_account_id,
            "amount": amount_paise,
            "currency": "INR",
            "mode": "UPI",
            "purpose": "payout",
            "queue_if_low_balance": True,
            "reference_id": reference_id,
            "narration": description[:30],
            "notes": {
                "partner_id": partner.id,
                "city": partner.city,
            },
        }

        created = await self._request("POST", "/v1/payouts", payload)
        payout_id = created.get("id")
        provider_status = (created.get("status") or "").lower()
        reference = created.get("utr") or payout_id or reference_id

        if not payout_id:
            raise RazorpayPayoutError("Razorpay payout created without payout id")

        return RazorpayPayoutResult(
            payout_id=payout_id,
            status=provider_status,
            reference=reference,
        )


razorpay_payout_service = RazorpayPayoutService()
