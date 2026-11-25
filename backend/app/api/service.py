"""Casos de uso que la API expone. Sin dependencias de FastAPI (testeable solo)."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..core.freshness import MADRID
from ..core.optimizer import optimize
from ..core.promotions import Channel
from .schemas import CompareIn, CompareOut, result_out, stores_domain


def compare(req: CompareIn, now: datetime | None = None) -> CompareOut:
    now = now or datetime.now(MADRID)
    items = [i.to_domain() for i in req.items]
    offers = {i.id: [o.to_domain() for o in i.offers] for i in req.items}
    stores = stores_domain(req.stores)
    result = optimize(
        items, offers, stores,
        max_stores=min(req.max_stores, len(stores)), day=req.shopping_day, now=now,
        max_age=timedelta(hours=req.max_age_hours),
        channel=Channel.ONLINE if req.channel == "online" else Channel.STORE,
        min_saving_per_extra_store=req.min_saving_per_extra_store_cents)
    return result_out(result)
