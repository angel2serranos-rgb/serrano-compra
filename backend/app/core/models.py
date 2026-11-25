"""Modelos de dominio (independientes de base de datos y de HTTP)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .money import Cents
from .promotions import Promotion
from .units import Quantity


class PriceKind(str, Enum):
    """De dónde sale el precio. Nunca se mezclan sin decirlo."""
    ONLINE = "online_oficial"
    STORE_VERIFIED = "tienda_verificado"
    FLYER = "folleto"
    RECEIPT = "ticket"
    ESTIMATED = "estimado"


# Orden de confianza (mayor = más fiable para compra presencial).
CONFIDENCE = {
    PriceKind.STORE_VERIFIED: 5, PriceKind.RECEIPT: 4, PriceKind.FLYER: 3,
    PriceKind.ONLINE: 3, PriceKind.ESTIMATED: 1,
}


@dataclass(frozen=True)
class Offer:
    """Un producto concreto con su precio en un supermercado y momento."""
    store_id: str
    product_id: str
    name: str
    brand: str
    price: Cents                       # precio por envase (o por kg si per_kg=True)
    pack: Quantity                     # contenido del envase; si per_kg, 1000 g
    observed_at: datetime              # con zona horaria
    kind: PriceKind
    source_url: str = ""
    is_private_label: bool = False
    ean: str | None = None
    per_kg: bool = False               # peso variable: precio es €/kg
    est_unit_g: tuple[Decimal, Decimal] | None = None  # (mín, máx) g por pieza, estimado
    attrs: dict[str, Decimal] = field(default_factory=dict)  # p. ej. {"meat_pct": 93}
    promo: Promotion | None = None
    available: bool = True


@dataclass(frozen=True)
class BasketItem:
    id: str
    label: str
    required: Quantity
    mandatory: bool = True
    brands: frozenset[str] | None = None          # None = cualquiera
    private_label_ok: bool = True
    min_attrs: dict[str, Decimal] = field(default_factory=dict)
    max_attrs: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class StoreCosts:
    """Costes de ir/pedir a un supermercado. Los fija el usuario, no se inventan."""
    store_id: str
    travel: Cents = 0                  # coste estimado de desplazamiento (presencial)
    delivery_fee: Cents = 0            # online
    min_order: Cents = 0               # online
    membership_ok: bool = False        # el usuario tiene tarjeta/club de esa cadena
