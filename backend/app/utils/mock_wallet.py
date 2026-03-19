"""
GridGuard AI — Mock Wallet Engine
Razorpay-compatible interface for wallet credit/debit operations
"""

from dataclasses import dataclass
from uuid import uuid4

from app.models.partner import Partner
from app.models.wallet_transaction import WalletTransaction


class InsufficientFundsError(Exception):
    """Raised when partner has insufficient wallet balance."""
    pass


@dataclass
class WalletResult:
    reference: str
    status: str
    new_balance: float


class MockWallet:
    """Mock payment wallet with atomic credit/debit — Razorpay-compatible shape."""

    async def credit(
        self,
        partner_id: str,
        amount: float,
        description: str,
    ) -> WalletResult:
        """
        Credit amount to partner wallet.
        Atomic: findOneAndUpdate $inc mock_wallet_balance +amount
        """
        from app.database import get_database

        db = get_database()
        result = await db["partners"].find_one_and_update(
            {"_id": partner_id},
            {"$inc": {"mock_wallet_balance": amount}},
            return_document=True,
        )

        if result is None:
            raise ValueError(f"Partner {partner_id} not found")

        new_balance = result["mock_wallet_balance"]
        reference = f"MOCK-CRED-{uuid4().hex[:8].upper()}"

        # Log wallet transaction
        tx = WalletTransaction(
            partner_id=partner_id,
            type="credit",
            amount=amount,
            reference=reference,
            description=description,
            balance_after=new_balance,
        )
        await tx.insert()

        return WalletResult(
            reference=reference,
            status="paid",
            new_balance=new_balance,
        )

    async def debit(
        self,
        partner_id: str,
        amount: float,
        description: str,
    ) -> WalletResult:
        """
        Debit amount from partner wallet.
        Check balance first, then atomic $inc -amount.
        """
        current = await self.get_balance(partner_id)
        if current < amount:
            raise InsufficientFundsError(
                f"Insufficient funds: balance={current}, debit={amount}"
            )

        from app.database import get_database

        db = get_database()
        result = await db["partners"].find_one_and_update(
            {"_id": partner_id},
            {"$inc": {"mock_wallet_balance": -amount}},
            return_document=True,
        )

        new_balance = result["mock_wallet_balance"]
        reference = f"MOCK-DEBI-{uuid4().hex[:8].upper()}"

        # Log wallet transaction
        tx = WalletTransaction(
            partner_id=partner_id,
            type="debit",
            amount=amount,
            reference=reference,
            description=description,
            balance_after=new_balance,
        )
        await tx.insert()

        return WalletResult(
            reference=reference,
            status="debited",
            new_balance=new_balance,
        )

    async def get_balance(self, partner_id: str) -> float:
        """Get current wallet balance for a partner."""
        partner = await Partner.get(partner_id)
        if partner is None:
            raise ValueError(f"Partner {partner_id} not found")
        return partner.mock_wallet_balance


mock_wallet = MockWallet()
