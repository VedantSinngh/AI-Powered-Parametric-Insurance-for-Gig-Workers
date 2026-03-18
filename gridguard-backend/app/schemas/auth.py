"""
GridGuard AI — Auth Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    device_id: str = Field(..., max_length=128)
    phone_number: str = Field(..., max_length=15)
    full_name: str = Field(..., max_length=128)
    platform: str = Field(..., description="zomato|swiggy|zepto|blinkit|other")
    city: str = Field(..., max_length=64)
    gps_lat: float | None = None
    gps_lng: float | None = None


class RegisterResponse(BaseModel):
    partner_id: UUID
    otp_session_token: str


class VerifyOTPRequest(BaseModel):
    otp_session_token: str
    otp_code: str = Field(..., min_length=4, max_length=6)


class VerifyOTPResponse(BaseModel):
    access_token: str
    refresh_token: str
    partner_id: UUID
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
