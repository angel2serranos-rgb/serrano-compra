"""Esquemas HTTP (Pydantic v2) y conversión a/desde el dominio."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..core.models import BasketItem, Offer, PriceKind, StoreCosts
from ..core.money import fmt_eur
from ..core.optimizer import OptimizationResult, Plan
from ..core.promotions import Channel, Promotion, PromoType
from ..core.units import Quantity


class QtyIn(BaseModel):
    amount: Decimal = Field(gt=0, le=100_000)
    unit: str = Field(min_length=1, max_length=12)

    def to_domain(self) -> Quantity:
        return Quantity.parse(self.amount, self.unit)


class PromoIn(BaseModel):
    type: PromoType
    valid_from: date
    valid_to: date
    n: int = Field(0, ge=0, le=100)
    m: int = Field(0, ge=0, le=100)
    pct: Decimal = Field(Decimal(0), ge=0, le=100)
    price_cents: int = Field(0, ge=0)
    channel: Channel = Channel.BOTH
    requires_membership: bool = False


class OfferIn(BaseModel):
    store_id: str = Field(pattern=r"^[a-z0-9_-]{1,32}$")
    product_id: str = Field(max_length=128)
    name: str = Field(max_length=300)
    brand: str = Field("", max_length=120)
    price_cents: int = Field(ge=0, le=10_000_000)
    pack: QtyIn
    observed_at: datetime
    kind: PriceKind
    source_url: str = Field("", max_length=1000)
    is_private_label: bool = False
    per_kg: bool = False
    est_unit_g: tuple[Decimal, Decimal] | None = None
    attrs: dict[str, Decimal] = {}
    promo: PromoIn | None = None
    available: bool = True

    @field_validator("observed_at")
    @classmethod
    def tz_required(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("observed_at debe incluir zona horaria")
        return v

    def to_domain(self) -> Offer:
        p = self.promo
        promo = None if p is None else Promotion(
            p.type, p.valid_from, p.valid_to, p.n, p.m, p.pct, p.price_cents, p.channel,
            p.requires_membership)
        return Offer(self.store_id, self.product_id, self.name, self.brand, self.price_cents,
                     self.pack.to_domain(), self.observed_at, self.kind, self.source_url,
                     self.is_private_label, None, self.per_kg, self.est_unit_g, dict(self.attrs),
                     promo, self.available)


class ItemIn(BaseModel):
    id: str = Field(max_length=64)
    label: str = Field(max_length=200)
    required: QtyIn
    mandatory: bool = True
    brands: list[str] | None = None
    private_label_ok: bool = True
    min_attrs: dict[str, Decimal] = {}
    max_attrs: dict[str, Decimal] = {}
    offers: list[OfferIn] = Field(default_factory=list, max_length=200)

    def to_domain(self) -> BasketItem:
        return BasketItem(self.id, self.label, self.required.to_domain(), self.mandatory,
                          frozenset(self.brands) if self.brands is not None else None,
                          self.private_label_ok, dict(self.min_attrs), dict(self.max_attrs))


class StoreCostsIn(BaseModel):
    store_id: str = Field(pattern=r"^[a-z0-9_-]{1,32}$")
    travel_cents: int = Field(0, ge=0)
    delivery_fee_cents: int = Field(0, ge=0)
    min_order_cents: int = Field(0, ge=0)
    membership_ok: bool = False


class CompareIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=100)
    stores: list[StoreCostsIn] = Field(min_length=1, max_length=20)
    max_stores: int = Field(1, ge=1, le=7)
    shopping_day: date
    channel: Literal["tienda", "online"] = "tienda"
    min_saving_per_extra_store_cents: int = Field(0, ge=0)
    max_age_hours: int = Field(36, ge=1, le=24 * 30)


class LineOut(BaseModel):
    item_id: str
    store_id: str
    product: str
    brand: str
    packs: int | None
    cost: str
    cost_range: str | None
    estimated: bool
    leftover: str
    promo: str
    price_kind: str
    observed_at: datetime
    source_url: str


class PlanOut(BaseModel):
    stores: list[str]
    complete: bool
    missing: list[str]
    subtotal: str
    extra_costs: str
    total: str
    total_cents: int
    has_estimates: bool
    lines: list[LineOut]


def plan_out(p: Plan) -> PlanOut:
    lines = [LineOut(
        item_id=q.item_id, store_id=q.offer.store_id, product=q.offer.name, brand=q.offer.brand,
        packs=q.packs, cost=fmt_eur(q.cost),
        cost_range=None if q.cost_low == q.cost_high else f"{fmt_eur(q.cost_low)} – {fmt_eur(q.cost_high)}",
        estimated=q.estimated, leftover=str(q.leftover), promo=q.promo_note,
        price_kind=q.offer.kind.value, observed_at=q.offer.observed_at,
        source_url=q.offer.source_url) for q in p.assignment.values()]
    return PlanOut(stores=list(p.stores), complete=p.complete, missing=p.missing,
                   subtotal=fmt_eur(p.subtotal), extra_costs=fmt_eur(p.extra_costs),
                   total=fmt_eur(p.total), total_cents=p.total, has_estimates=p.has_estimates,
                   lines=lines)


class CompareOut(BaseModel):
    chosen: PlanOut | None
    best_by_size: dict[int, PlanOut]
    best_incomplete: PlanOut | None
    saving_vs_best_single: str | None
    exclusions: list[dict]
    warning: str = ("Precios online usados como referencia: el precio en tienda física "
                    "puede diferir. Verifica con el ticket.")


def result_out(r: OptimizationResult) -> CompareOut:
    s = r.saving_vs_best_single()
    return CompareOut(
        chosen=plan_out(r.chosen) if r.chosen else None,
        best_by_size={k: plan_out(v) for k, v in r.best_by_size.items()},
        best_incomplete=plan_out(r.best_incomplete) if r.best_incomplete else None,
        saving_vs_best_single=None if s is None else fmt_eur(s),
        exclusions=[e.__dict__ for e in r.exclusions])


def stores_domain(stores: list[StoreCostsIn]) -> dict[str, StoreCosts]:
    return {s.store_id: StoreCosts(s.store_id, s.travel_cents, s.delivery_fee_cents,
                                   s.min_order_cents, s.membership_ok) for s in stores}
