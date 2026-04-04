"""
GridGuard AI — Wallet Router
Partner wallet APIs for top-up and withdrawal in sandbox mode.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.partner import Partner
from app.models.wallet_transaction import WalletTransaction
from app.schemas.schemas import WalletAdjustRequest
from app.core.dependencies import get_current_partner
from app.utils.mock_wallet import mock_wallet, InsufficientFundsError

router = APIRouter(prefix="/wallet", tags=["wallet"])


def _categorize_transaction(tx: WalletTransaction) -> str:
    description = (tx.description or "").strip().lower()
    reference = (tx.reference or "").strip().upper()

    if "signup bonus" in description or "SIGNUP-BONUS" in reference:
        return "signup_bonus"
    if "weekly premium" in description:
        return "premium_deduction"
    if "payout" in description:
        return "payout_credit"
    if "withdraw" in description:
        return "withdrawal"
    if "top-up" in description or "topup" in description:
        return "manual_addition"
    if tx.type == "credit" and reference.startswith("MOCK-CRED"):
        return "manual_addition"
    return "adjustment"


@router.get("/balance")
async def get_wallet_balance(
    partner: Partner = Depends(get_current_partner),
):
    """Return wallet balance and latest UPI handle for the current partner."""
    return {
        "partner_id": partner.id,
        "balance": partner.mock_wallet_balance,
        "upi_handle": partner.upi_handle,
        "updated_at": partner.updated_at,
    }


@router.post("/topup")
async def topup_wallet(
    _req: WalletAdjustRequest,
    _partner: Partner = Depends(get_current_partner),
):
    """Manual top-up is intentionally disabled for rider realism."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Manual add money is disabled. Wallet updates come from payouts, "
            "policy deductions, and withdrawals."
        ),
    )


@router.post("/withdraw")
async def withdraw_wallet(
    req: WalletAdjustRequest,
    partner: Partner = Depends(get_current_partner),
):
    """Sandbox-only withdrawal action used from rider dashboard."""
    if not partner.upi_handle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please set your UPI handle in profile before withdrawing",
        )

    try:
        result = await mock_wallet.debit(
            partner.id,
            req.amount,
            req.note or f"Withdrawal to {partner.upi_handle}",
        )
    except InsufficientFundsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    partner.updated_at = datetime.utcnow()
    await partner.save()

    return {
        "status": "success",
        "reference": result.reference,
        "balance": result.new_balance,
        "destination": partner.upi_handle,
    }


@router.get("/ledger")
async def get_wallet_ledger(
    limit: int = Query(20, ge=1, le=100),
    partner: Partner = Depends(get_current_partner),
):
    """Return wallet transaction history + rollups for payouts/additions/deductions."""
    latest_transactions = (
        await WalletTransaction.find(WalletTransaction.partner_id == partner.id)
        .sort(-WalletTransaction.created_at)
        .limit(limit)
        .to_list()
    )

    all_transactions = await WalletTransaction.find(
        WalletTransaction.partner_id == partner.id
    ).to_list()

    summary = {
        "total_credits": 0.0,
        "total_debits": 0.0,
        "payout_credits": 0.0,
        "manual_additions": 0.0,
        "premium_deductions": 0.0,
        "withdrawals": 0.0,
    }

    for tx in all_transactions:
        category = _categorize_transaction(tx)
        amount = float(tx.amount)

        if tx.type == "credit":
            summary["total_credits"] += amount
        else:
            summary["total_debits"] += amount

        if category == "payout_credit":
            summary["payout_credits"] += amount
        elif category == "manual_addition":
            summary["manual_additions"] += amount
        elif category == "premium_deduction":
            summary["premium_deductions"] += amount
        elif category == "withdrawal":
            summary["withdrawals"] += amount

    return {
        "partner_id": partner.id,
        "balance": partner.mock_wallet_balance,
        "updated_at": partner.updated_at,
        "summary": {key: round(value, 2) for key, value in summary.items()},
        "transactions": [
            {
                "id": tx.id,
                "type": tx.type,
                "category": _categorize_transaction(tx),
                "amount": tx.amount,
                "reference": tx.reference,
                "description": tx.description,
                "balance_after": tx.balance_after,
                "created_at": tx.created_at,
            }
            for tx in latest_transactions
        ],
    }
