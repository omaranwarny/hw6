"""Structured types for the Campus Customs vendor desk agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Check = Literal["approved_vendor", "price", "lead_time", "minimum_order"]


class VendorDecision(BaseModel):
    """The agent's answer for one vendor document (handbook section 13)."""

    vendor: str = Field(description="Vendor name exactly as the document gives it")
    sku: str | None = Field(description="Campus Customs SKU, e.g. 'CC-HD-006'; null if the document doesn't say")
    unit_price: float | None = Field(description="Quoted unit price in USD from the document; null if not stated")
    lead_time_days: int | None = Field(description="Lead time in days as quoted (e.g. '14 business days' -> 14); null if not stated")
    min_order: int | None = Field(description="Minimum order in units; null if not stated")
    decision: Literal["recommend", "do_not_recommend"]
    failed_check: Check | None = Field(
        default=None, description="The first purchasing check that failed (null when recommending)")
    reason: str = Field(description="One sentence naming the purchasing check that decided it")
