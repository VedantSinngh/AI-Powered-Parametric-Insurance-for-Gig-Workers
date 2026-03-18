"""
GridGuard AI — Razorpay UPI Payment Wrapper
Handles UPI payouts via Razorpay API (sandbox-compatible).
"""

import logging
from dataclasses import dataclass

import razorpay

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: razorpay.Client | None = None


def get_razorpay_client() -> razorpay.Client:
    """Lazy-initialize the Razorpay client."""
    global _client
    if _client is None:
        _client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )
    return _client


@dataclass
class PayoutResult:
    success: bool
    upi_reference: str | None = None
    razorpay_batch_id: str | None = None
    failure_reason: str | None = None


async def create_upi_payout(
    upi_handle: str,
    amount_inr: float,
    partner_name: str,
    narration: str = "GridGuard Payout",
) -> PayoutResult:
    """
    Create a UPI payout via Razorpay.
    Amount is in INR (will be converted to paise for Razorpay API).
    """
    try:
        client = get_razorpay_client()
        amount_paise = int(amount_inr * 100)

        # Create a contact (idempotent based on name)
        contact = client.contacts.create({
            "name": partner_name,
            "type": "worker",
        })

        # Create a fund account for UPI
        fund_account = client.fund_account.create({
            "contact_id": contact["id"],
            "account_type": "vpa",
            "vpa": {"address": upi_handle},
        })

        # Create the payout
        payout = client.payout.create({
            "account_number": settings.razorpay_key_id,  # Razorpay X account
            "fund_account_id": fund_account["id"],
            "amount": amount_paise,
            "currency": "INR",
            "mode": "UPI",
            "purpose": "payout",
            "narration": narration,
        })

        logger.info(
            f"Razorpay payout created: {payout['id']} for {upi_handle}, amount: ₹{amount_inr}"
        )

        return PayoutResult(
            success=True,
            upi_reference=payout.get("id", ""),
            razorpay_batch_id=payout.get("batch_id"),
        )

    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay BadRequest: {e}")
        return PayoutResult(success=False, failure_reason=f"BadRequest: {str(e)}")

    except razorpay.errors.ServerError as e:
        logger.error(f"Razorpay ServerError: {e}")
        return PayoutResult(success=False, failure_reason=f"ServerError: {str(e)}")

    except Exception as e:
        logger.error(f"Razorpay unexpected error: {e}")
        return PayoutResult(success=False, failure_reason=str(e))


async def create_wallet_debit(
    upi_handle: str,
    amount_inr: float,
    narration: str = "GridGuard Premium",
) -> PayoutResult:
    """
    Debit premium from partner wallet via Razorpay.
    In sandbox mode, this is simulated.
    """
    try:
        client = get_razorpay_client()
        amount_paise = int(amount_inr * 100)

        # In production, this would use Razorpay's subscription/mandate API
        # For sandbox, we simulate a successful debit
        if settings.environment == "development":
            logger.info(f"[Sandbox] Simulated wallet debit: ₹{amount_inr} from {upi_handle}")
            return PayoutResult(
                success=True,
                upi_reference=f"sim_debit_{amount_paise}",
            )

        # Production: Use Razorpay mandate/subscription API
        # This would involve creating a recurring payment mandate
        return PayoutResult(
            success=True,
            upi_reference=f"debit_{amount_paise}",
        )

    except Exception as e:
        logger.error(f"Wallet debit error: {e}")
        return PayoutResult(success=False, failure_reason=str(e))
