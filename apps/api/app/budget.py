"""Atomic application budget reservations, in millionths of one US dollar.

Pricing verified against Meta's official pricing page on 2026-10-31.
Provider billing is authoritative. Unknown outcomes retain their conservative
reservation as estimated usage, rather than silently freeing possible spend.
"""
from __future__ import annotations

import math
import os

from fastapi import HTTPException
from sqlalchemy import update

from domain.models import new_id
from .database import BudgetRow, MetaUsageRow, now

RATES = {"muse-wonder-1.0": (4.0, .20, 20.0), "muse-spark-1.3": (1.25, .15, 4.25)}


def ceiling_microusd() -> int:
    value = float(os.environ.get("APP_SPEND_CEILING_USD", "135"))
    if not math.isfinite(value) or value < 0:
        raise HTTPException(503, "The application spending ceiling is not configured correctly.")
    return round(value * 1_000_000)


def reserve(factory, amount: int):
    with factory.begin() as db:
        result = db.execute(update(BudgetRow).where(
            BudgetRow.id == "application",
            BudgetRow.spent_microusd + BudgetRow.reserved_microusd + amount <= ceiling_microusd(),
        ).values(reserved_microusd=BudgetRow.reserved_microusd + amount))
        if result.rowcount != 1:
            raise HTTPException(429, {"code": "BUDGET_CEILING", "message": "The Meta spending ceiling has been reserved or reached. Direct editing, calculations and exports are still available."})


def settle(factory, reservation: int, kind: str, model: str, usage: dict | None, audio_ms: int = 0, *, billing_rejected: bool = False):
    reported = usage is not None or audio_ms > 0
    usage = usage or {}
    inp = max(0, int(usage.get("input_tokens", 0) or 0))
    cached = min(inp, max(0, int((usage.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0)))
    output = max(0, int(usage.get("output_tokens", 0) or 0))
    if billing_rejected:
        # An HTTP 402 rejects work before acceptance; unlike a timeout its cost
        # is known to be zero. Keep an explicit receipt, without inventing usage.
        inp = cached = output = audio_ms = 0
        cost = 0
    elif kind == "transcription" and reported:
        cost = math.ceil(audio_ms / 1000) * .18 / 3600 * 1_000_000
    elif reported:
        rates = RATES[model]
        cost = (inp - cached) * rates[0] + cached * rates[1] + output * rates[2]
    else:
        cost = reservation
    with factory.begin() as db:
        db.execute(update(BudgetRow).where(BudgetRow.id == "application").values(
            reserved_microusd=BudgetRow.reserved_microusd - reservation,
            spent_microusd=BudgetRow.spent_microusd + round(cost)))
        receipt_kind = f"{kind}_billing_rejected" if billing_rejected else (kind if reported else f"{kind}_unknown_cost")
        db.add(MetaUsageRow(id=new_id(), created_at=now(), kind=receipt_kind,
                            model=model, input_tokens=inp, cached_tokens=cached, output_tokens=output,
                            audio_ms=audio_ms, est_cost_usd=f"{cost / 1_000_000:.6f}"))


def summary(db):
    budget = db.get(BudgetRow, "application")
    usage = db.query(MetaUsageRow).all()
    return {"calls": len(usage), "est_total_usd": budget.spent_microusd / 1_000_000,
            "reserved_usd": budget.reserved_microusd / 1_000_000,
            "ceiling_usd": ceiling_microusd() / 1_000_000,
            "input_tokens": sum(row.input_tokens for row in usage),
            "output_tokens": sum(row.output_tokens for row in usage),
            "pricing_basis": "https://dev.meta.ai/docs/pricing-rate-limits; verified 2026-10-31; provider billing authoritative"}
