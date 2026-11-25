"""Motor de optimización de la cesta.

Método: enumeración EXACTA de todas las combinaciones de supermercados
(con 7 cadenas hay 127 combinaciones), asignando cada producto al más barato
de la combinación. Es verificable y no depende de ningún modelo de IA.

Reglas no negociables implementadas aquí:
- Un producto que no cumple requisitos (marca, % carne...) no entra.
- Un requisito sin verificar (dato ausente) excluye el producto.
- Precios caducados no entran.
- Una cesta a la que le falta un producto obligatorio NO es completa.
- Solo se añade otro supermercado si el ahorro supera el umbral del usuario.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from itertools import combinations

from .freshness import is_fresh
from .models import CONFIDENCE, BasketItem, Offer, StoreCosts
from .money import Cents, mul_round
from .promotions import Channel, cost_for_units
from .units import Unit

EXTRA_PACKS_TO_TRY = 2  # p. ej. con 3x2 puede salir igual llevar 3 que 2


@dataclass(frozen=True)
class Quote:
    item_id: str
    offer: Offer
    packs: int | None
    cost: Cents              # coste esperado (el que se usa para optimizar)
    cost_low: Cents
    cost_high: Cents
    leftover: Decimal        # sobrante en unidad base (g, ml, ud)
    estimated: bool          # hay pesos estimados
    promo_note: str
    future_balance: Cents


@dataclass(frozen=True)
class Exclusion:
    item_id: str
    store_id: str
    product_id: str
    reason: str


@dataclass
class Plan:
    stores: tuple[str, ...]
    assignment: dict[str, Quote]
    missing: list[str]
    subtotal: Cents
    extra_costs: Cents
    notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> Cents:
        return self.subtotal + self.extra_costs

    @property
    def complete(self) -> bool:
        return not self.missing

    @property
    def has_estimates(self) -> bool:
        return any(q.estimated for q in self.assignment.values())

    @property
    def min_confidence(self) -> int:
        return min((CONFIDENCE[q.offer.kind] for q in self.assignment.values()), default=0)


@dataclass
class OptimizationResult:
    chosen: Plan | None
    best_by_size: dict[int, Plan]
    best_incomplete: Plan | None
    exclusions: list[Exclusion]

    def saving_vs_best_single(self) -> Cents | None:
        single = self.best_by_size.get(1)
        if not self.chosen or not single:
            return None
        return single.total - self.chosen.total


# ---------------------------------------------------------------- requisitos

def constraint_failure(item: BasketItem, offer: Offer) -> str | None:
    if not offer.available:
        return "agotado / no disponible"
    if item.brands is not None and offer.brand.lower() not in {b.lower() for b in item.brands}:
        return f"marca {offer.brand!r} no permitida"
    if offer.is_private_label and not item.private_label_ok:
        return "marca blanca rechazada por el usuario"
    for key, minimum in item.min_attrs.items():
        val = offer.attrs.get(key)
        if val is None:
            return f"{key} sin verificar (pendiente)"
        if val < minimum:
            return f"{key}={val} inferior al mínimo {minimum}"
    for key, maximum in item.max_attrs.items():
        val = offer.attrs.get(key)
        if val is None:
            return f"{key} sin verificar (pendiente)"
        if val > maximum:
            return f"{key}={val} superior al máximo {maximum}"
    return None


# ---------------------------------------------------------------- coste

def quote(item: BasketItem, offer: Offer, day: date, *, user_eligible: bool,
          channel: Channel) -> Quote | str:
    """Coste de cubrir `item` con `offer`. Devuelve Quote o motivo de no comparabilidad."""
    req = item.required
    if offer.per_kg:
        if req.unit == Unit.G:
            cost = mul_round(offer.price, req.amount / Decimal(1000))
            return Quote(item.id, offer, None, cost, cost, cost, Decimal(0), False,
                         "precio por kg (peso variable en caja)", 0)
        if req.unit == Unit.UD and offer.est_unit_g:
            lo_g, hi_g = offer.est_unit_g
            low = mul_round(offer.price, req.amount * lo_g / Decimal(1000))
            high = mul_round(offer.price, req.amount * hi_g / Decimal(1000))
            mid = mul_round(offer.price, req.amount * (lo_g + hi_g) / 2 / Decimal(1000))
            return Quote(item.id, offer, None, mid, low, high, Decimal(0), True,
                         f"ESTIMADO: {lo_g}-{hi_g} g por pieza", 0)
        return "vendido por kg sin peso por pieza conocido: no comparable"

    if offer.pack.unit != req.unit:
        return f"formato no comparable ({offer.pack.unit.value} vs {req.unit.value})"
    needed = math.ceil(req.amount / offer.pack.amount)
    best = None
    for n in range(needed, needed + EXTRA_PACKS_TO_TRY + 1):
        r = cost_for_units(offer.price, n, offer.promo, day,
                           user_eligible=user_eligible, channel=channel)
        if best is None or r.pay_now < best[1].pay_now:
            best = (n, r)
    n, r = best
    leftover = n * offer.pack.amount - req.amount
    return Quote(item.id, offer, n, r.pay_now, r.pay_now, r.pay_now, leftover, False,
                 r.note, r.future_balance)


# ---------------------------------------------------------------- optimización

def best_quotes(items, offers_by_item, stores, *, day, now, max_age, channel):
    quotes: dict[str, dict[str, Quote]] = {}
    exclusions: list[Exclusion] = []
    for item in items:
        per_store: dict[str, Quote] = {}
        for offer in offers_by_item.get(item.id, []):
            if offer.store_id not in stores:
                continue
            if not is_fresh(offer.observed_at, now, max_age):
                exclusions.append(Exclusion(item.id, offer.store_id, offer.product_id,
                                            "precio caducado"))
                continue
            fail = constraint_failure(item, offer)
            if fail:
                exclusions.append(Exclusion(item.id, offer.store_id, offer.product_id, fail))
                continue
            q = quote(item, offer, day, user_eligible=stores[offer.store_id].membership_ok,
                      channel=channel)
            if isinstance(q, str):
                exclusions.append(Exclusion(item.id, offer.store_id, offer.product_id, q))
                continue
            cur = per_store.get(offer.store_id)
            if cur is None or (q.cost, q.offer.product_id) < (cur.cost, cur.offer.product_id):
                per_store[offer.store_id] = q
        quotes[item.id] = per_store
    return quotes, exclusions


def _plan(combo, items, quotes, stores, channel) -> Plan | None:
    assignment: dict[str, Quote] = {}
    missing: list[str] = []
    for item in items:
        options = [quotes[item.id][s] for s in combo if s in quotes[item.id]]
        if not options:
            if item.mandatory:
                missing.append(item.id)
            continue
        assignment[item.id] = min(options, key=lambda q: (q.cost, q.offer.store_id))
    used = tuple(sorted({q.offer.store_id for q in assignment.values()}))
    if used != combo:          # alguna tienda no aporta nada: esa combinación ya existe más pequeña
        return None
    subtotal = sum(q.cost for q in assignment.values())
    extra = 0
    notes: list[str] = []
    for s in used:
        sc = stores[s]
        if channel == Channel.ONLINE:
            store_sub = sum(q.cost for q in assignment.values() if q.offer.store_id == s)
            if store_sub < sc.min_order:
                notes.append(f"{s}: no llega al pedido mínimo")
                return None
            extra += sc.delivery_fee
        else:
            extra += sc.travel
    return Plan(used, assignment, missing, subtotal, extra, notes)


def optimize(items: list[BasketItem], offers_by_item: dict[str, list[Offer]],
             stores: dict[str, StoreCosts], *, max_stores: int, day: date, now: datetime,
             max_age: timedelta = timedelta(hours=36), channel: Channel = Channel.STORE,
             min_saving_per_extra_store: Cents = 0) -> OptimizationResult:
    if not 1 <= max_stores <= len(stores):
        raise ValueError("max_stores fuera de rango")
    quotes, exclusions = best_quotes(items, offers_by_item, stores, day=day, now=now,
                                     max_age=max_age, channel=channel)
    store_ids = sorted(stores)
    best_by_size: dict[int, Plan] = {}
    best_incomplete: Plan | None = None
    for size in range(1, max_stores + 1):
        for combo in combinations(store_ids, size):
            plan = _plan(combo, items, quotes, stores, channel)
            if plan is None:
                continue
            key = (plan.total, plan.stores)
            if plan.complete:
                cur = best_by_size.get(size)
                if cur is None or key < (cur.total, cur.stores):
                    best_by_size[size] = plan
            else:
                k2 = (len(plan.missing), plan.total, plan.stores)
                if best_incomplete is None or k2 < (len(best_incomplete.missing),
                                                    best_incomplete.total, best_incomplete.stores):
                    best_incomplete = plan

    chosen: Plan | None = None
    for size in sorted(best_by_size):
        cand = best_by_size[size]
        if chosen is None:
            chosen = cand
            continue
        extra_stores = len(cand.stores) - len(chosen.stores)
        required_saving = max(1, min_saving_per_extra_store * extra_stores)
        if chosen.total - cand.total >= required_saving:
            chosen = cand
    return OptimizationResult(chosen, best_by_size, best_incomplete, exclusions)
