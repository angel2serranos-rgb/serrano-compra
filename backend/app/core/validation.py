"""Controles de plausibilidad antes de aceptar un precio.

Motivo: hasta los comparadores comerciales publican errores (p. ej. un kilo de
jamón a 1,85 €/kg o leche a 954 €/l). Un precio que falla un control NO se descarta
en silencio: se guarda como 'en cuarentena' y se avisa.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import Cents
from .units import Quantity, unit_price

# Rango razonable de €/kg o €/l por familia (céntimos). Ajustable; amplio a propósito.
PLAUSIBLE_PER_BASE: dict[str, tuple[Cents, Cents]] = {
    "default": (5, 30_000),          # 0,05 €/kg – 300 €/kg
    "leche": (30, 1_000),            # 0,30 – 10 €/l
    "jamon_cocido": (400, 6_000),    # 4 – 60 €/kg
    "fruta_verdura": (20, 2_500),
}


@dataclass(frozen=True)
class Check:
    ok: bool
    problems: tuple[str, ...]


def check_price(price: Cents, pack: Quantity, *, family: str = "default",
                shown_unit_price: Cents | None = None, previous: Cents | None = None,
                max_jump_pct: int = 60) -> Check:
    problems: list[str] = []
    if price <= 0:
        problems.append("precio <= 0")
        return Check(False, tuple(problems))
    up, label = unit_price(price, pack)
    lo, hi = PLAUSIBLE_PER_BASE.get(family, PLAUSIBLE_PER_BASE["default"])
    if label in ("€/kg", "€/l") and not lo <= up <= hi:
        problems.append(f"{label} implausible para {family}: {up} céntimos")
    if shown_unit_price is not None and abs(shown_unit_price - up) > 1:
        problems.append(f"precio unitario publicado ({shown_unit_price}) ≠ calculado ({up})")
    if previous:
        jump = abs(price - previous) * 100 / previous
        if jump > max_jump_pct:
            problems.append(f"cambio del {jump:.0f}% respecto al último precio")
    return Check(not problems, tuple(problems))


def shrinkflation(prev_pack: Quantity, new_pack: Quantity, prev_price: Cents,
                  new_price: Cents) -> Decimal | None:
    """% de subida del precio por unidad cuando el envase encoge. None si no aplica."""
    if not prev_pack.same_dimension(new_pack) or new_pack.amount >= prev_pack.amount:
        return None
    old_up, _ = unit_price(prev_price, prev_pack)
    new_up, _ = unit_price(new_price, new_pack)
    if new_up <= old_up:
        return None
    return (Decimal(new_up - old_up) * 100 / Decimal(old_up)).quantize(Decimal("0.1"))
