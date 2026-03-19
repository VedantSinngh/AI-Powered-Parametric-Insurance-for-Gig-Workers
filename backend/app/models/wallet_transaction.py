"""
WalletTransaction Document — Mock wallet ledger
Collection: wallet_transactions
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Literal


class WalletTransaction(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    partner_id: str = Indexed()
    type: Literal["credit", "debit"] = Indexed()
    amount: float
    reference: str
    description: str
    balance_after: float
    created_at: datetime = Indexed(default_factory=datetime.utcnow)

    class Settings:
        name = "wallet_transactions"
