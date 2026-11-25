"""Lector específico de fichas de Ahorramás.

Formato observado en fichas reales (reconocimiento desde GitHub, 25/11/2026):
  envase fijo   : "Jamón cocido ... Noel 120g 2 ,39€ 1.0 Kg --> 19,92€/KILO"
  peso variable : "Jamón cocido extra Campofrío 14 ,29€ 1.0 Kg --> 14,29€/Kg  Peso 100 gr ..."
  pieza aprox.  : "Aguacate 5 ,99€ 1.0 Kg --> 5,99€/Kg Peso Unidades 300 gr ... Peso aprox unidad 300 gr"
El JSON-LD trae nombre, marca, sku y precio, pero NO la unidad: un 14.29 puede ser
el envase o el kilo. Por eso se combina JSON-LD (fuente del precio) + texto visible
(fuente de la unidad), y se exige que ambos cuadren. Si no cuadran → None.
"""
from __future__ import annotations

import html as htmlmod
import re
from dataclasses import dataclass
from decimal import Decimal

from ..core.money import Cents, to_cents
from .jsonld import parse_product

_TAGS = re.compile(r"<script.*?</script>|<style.*?</style>|<[^>]+>", re.DOTALL | re.IGNORECASE)
_PRICE_BLOCK = r"\s+(\d+)\s*,\s*(\d{2})\s*€\s*[\d.,]+\s*Kg\s*-->\s*(\d+,\d{2})\s*€\s*/\s*(Kg|KILO|L|LITRO|LT|Ud|UNIDAD)"
_APPROX_UNIT = re.compile(r"Peso aprox\.? unidad\s+(\d+)\s*gr", re.IGNORECASE)
_WEIGHT_SELECTOR = re.compile(r"\bPeso(?:\s+Unidades)?\s+\d+\s*gr\b", re.IGNORECASE)
_NAME_QTY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr|ml|cl|l)\b", re.IGNORECASE)

APPROX_TOLERANCE = Decimal("0.15")   # SUPUESTO: ±15 % sobre el "peso aprox." publicado


@dataclass(frozen=True)
class AhorramasItem:
    sku: str
    name: str
    brand: str | None
    price: Cents                 # precio de venta (envase) o €/kg si per_kg
    unit_price: Cents            # precio por kg/l publicado
    unit_label: str              # "kg" | "l" | "ud"
    per_kg: bool
    pack_g: Decimal | None       # contenido derivado (envase fijo)
    est_unit_g: tuple[Decimal, Decimal] | None
    available: bool | None


def visible_text(html: str) -> str:
    return " ".join(htmlmod.unescape(_TAGS.sub(" ", html)).split())


def parse(html: str, url: str) -> AhorramasItem | None:
    p = parse_product(html, store_id="ahorramas", url=url)
    if not p or not p.price_text or not p.name:
        return None
    text = visible_text(html)
    m = re.search(re.escape(p.name) + _PRICE_BLOCK, text)
    if not m:
        return None
    shown = to_cents(f"{m.group(1)},{m.group(2)}")
    if shown != to_cents(p.price_text):          # el texto y el JSON-LD deben coincidir
        return None
    unit_price = to_cents(m.group(3))
    unit = {"kg": "kg", "kilo": "kg", "l": "l", "litro": "l", "lt": "l"}.get(m.group(4).lower(), "ud")
    weight_selector = bool(_WEIGHT_SELECTOR.search(text[m.end(): m.end() + 400]))
    per_kg = unit == "kg" and shown == unit_price and weight_selector

    pack_g = None
    if not per_kg and unit in ("kg", "l") and unit_price > 0:
        pack_g = (Decimal(shown) * 1000 / Decimal(unit_price)).quantize(Decimal(1))
        nm = _NAME_QTY.search(p.name)
        if nm:                                   # contrastar con el nombre ("120g")
            q = Decimal(nm.group(1).replace(",", "."))
            q *= {"kg": 1000, "l": 1000, "cl": 10}.get(nm.group(2).lower(), 1)
            if abs(q - pack_g) > max(Decimal(5), q * Decimal("0.03")):
                return None                      # no cuadra: mejor no dar dato
            pack_g = q

    est = None
    am = _APPROX_UNIT.search(text)
    if per_kg and am:
        g = Decimal(am.group(1))
        est = ((g * (1 - APPROX_TOLERANCE)).quantize(Decimal(1)),
               (g * (1 + APPROX_TOLERANCE)).quantize(Decimal(1)))

    return AhorramasItem(p.external_id, p.name, p.brand, shown, unit_price, unit, per_kg,
                         pack_g, est, p.available)
