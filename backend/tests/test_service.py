"""Prueba el caso de uso /compare sin servidor HTTP. Datos SIMULADOS."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.api.schemas import CompareIn
from app.api.service import compare
from app.core.freshness import MADRID

NOW = datetime(2026, 11, 28, 9, 50, tzinfo=MADRID)


def payload(**over):
    base = {
        "shopping_day": "2026-11-28", "max_stores": 2,
        "stores": [{"store_id": "a", "travel_cents": 0}, {"store_id": "b", "travel_cents": 0}],
        "items": [{
            "id": "leche", "label": "6 l leche", "required": {"amount": 6, "unit": "l"},
            "offers": [
                {"store_id": "a", "product_id": "la", "name": "Leche A", "price_cents": 99,
                 "pack": {"amount": 1, "unit": "l"}, "observed_at": "2026-11-28T06:05:00+01:00",
                 "kind": "online_oficial",
                 "promo": {"type": "n_for_m", "valid_from": "2026-11-01",
                           "valid_to": "2026-11-30", "n": 3, "m": 2}},
                {"store_id": "b", "product_id": "lb", "name": "Leche B", "price_cents": 75,
                 "pack": {"amount": 1, "unit": "l"}, "observed_at": "2026-11-28T06:05:00+01:00",
                 "kind": "folleto"},
            ]}],
    }
    base.update(over)
    return base


def test_compare_end_to_end():
    out = compare(CompareIn.model_validate(payload()), now=NOW)
    # A: 6 l con 3x2 = 4 × 0,99 = 3,96 € ; B: 6 × 0,75 = 4,50 €
    assert out.chosen.total == "3,96 €" and out.chosen.stores == ["a"]
    assert out.chosen.lines[0].promo.startswith("3x2")


def test_naive_datetime_rejected():
    bad = payload()
    bad["items"][0]["offers"][0]["observed_at"] = "2026-11-28T06:05:00"
    with pytest.raises(ValidationError):
        CompareIn.model_validate(bad)


def test_float_like_negative_price_rejected():
    bad = payload()
    bad["items"][0]["offers"][0]["price_cents"] = -1
    with pytest.raises(ValidationError):
        CompareIn.model_validate(bad)
