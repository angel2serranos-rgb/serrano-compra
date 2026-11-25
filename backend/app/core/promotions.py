"""Motor de promociones: calcula el coste REAL de comprar n envases.

Distingue descuento inmediato (rebaja el pago) de saldo futuro (cheque ahorro):
el saldo futuro NUNCA se resta del coste de hoy; se informa aparte.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from .money import Cents, mul_round


class PromoType(str, Enum):
    N_FOR_M = "n_for_m"              # 2x1, 3x2: llevas n, pagas m
    NTH_UNIT_PCT = "nth_unit_pct"    # 2ª unidad al 50 % / 70 % de descuento
    DIRECT_PCT = "direct_pct"        # -20 %
    PROMO_PRICE = "promo_price"      # precio rebajado fijo por unidad
    QTY_PRICE = "qty_price"          # desde X uds, precio unitario Y
    FUTURE_BALANCE_PCT = "future_balance_pct"  # % que vuelve como saldo/cheque


class Channel(str, Enum):
    ONLINE = "online"
    STORE = "tienda"
    BOTH = "ambos"


@dataclass(frozen=True)
class Promotion:
    type: PromoType
    valid_from: date
    valid_to: date
    n: int = 0                       # N_FOR_M / NTH_UNIT_PCT (n-ésima) / QTY_PRICE (mínimo)
    m: int = 0                       # N_FOR_M
    pct: Decimal = Decimal(0)        # descuento en % (0-100)
    price: Cents = 0                 # PROMO_PRICE / QTY_PRICE
    channel: Channel = Channel.BOTH
    requires_membership: bool = False  # club, socio, cupón personal
    conditions: str = ""

    def active_on(self, day: date) -> bool:
        return self.valid_from <= day <= self.valid_to


@dataclass(frozen=True)
class PromoResult:
    pay_now: Cents          # lo que pagas en caja
    future_balance: Cents   # saldo que recibes para otra compra (no es ahorro de hoy)
    applied: bool
    note: str


def cost_for_units(
    unit_price: Cents,
    units: int,
    promo: Promotion | None,
    day: date,
    *,
    user_eligible: bool = False,
    channel: Channel = Channel.STORE,
) -> PromoResult:
    """Coste de `units` envases a `unit_price`, aplicando `promo` si procede."""
    if units < 0:
        raise ValueError("units < 0")
    base = unit_price * units
    if promo is None or units == 0:
        return PromoResult(base, 0, False, "sin promoción")
    if not promo.active_on(day):
        return PromoResult(base, 0, False, "promoción fuera de vigencia")
    if promo.channel not in (Channel.BOTH, channel):
        return PromoResult(base, 0, False, f"promoción solo {promo.channel.value}")
    if promo.requires_membership and not user_eligible:
        return PromoResult(base, 0, False, "requiere socio/cupón: no verificado")

    t = promo.type
    if t == PromoType.N_FOR_M:
        groups, rest = divmod(units, promo.n)
        pay = (groups * promo.m + rest) * unit_price
        return PromoResult(pay, 0, groups > 0, f"{promo.n}x{promo.m} en {groups} grupo(s)")
    if t == PromoType.NTH_UNIT_PCT:
        groups, rest = divmod(units, promo.n)
        discounted = mul_round(unit_price, (Decimal(100) - promo.pct) / Decimal(100))
        pay = groups * ((promo.n - 1) * unit_price + discounted) + rest * unit_price
        return PromoResult(pay, 0, groups > 0, f"{promo.n}ª ud -{promo.pct}% x{groups}")
    if t == PromoType.DIRECT_PCT:
        each = mul_round(unit_price, (Decimal(100) - promo.pct) / Decimal(100))
        return PromoResult(each * units, 0, True, f"-{promo.pct}%")
    if t == PromoType.PROMO_PRICE:
        return PromoResult(promo.price * units, 0, True, "precio promocional")
    if t == PromoType.QTY_PRICE:
        if units >= promo.n:
            return PromoResult(promo.price * units, 0, True, f"desde {promo.n} uds")
        return PromoResult(base, 0, False, f"faltan uds para mínimo de {promo.n}")
    if t == PromoType.FUTURE_BALANCE_PCT:
        bal = mul_round(base, promo.pct / Decimal(100))
        return PromoResult(base, bal, True, f"{promo.pct}% como saldo futuro")
    raise ValueError(f"Tipo de promoción no soportado: {t}")
