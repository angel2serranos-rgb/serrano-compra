"""Porcentaje del ingrediente principal a partir de la lista de ingredientes.

Solo se acepta un porcentaje ESCRITO en la etiqueta (p. ej. "Jamón de cerdo 92%").
Si no aparece, devuelve None → el producto queda "pendiente de verificar" y se
excluye de las cestas que exigen un mínimo.
"""
from __future__ import annotations

import re
from decimal import Decimal

# ingrediente cárnico seguido (o precedido entre paréntesis) de un porcentaje
_MEAT = re.compile(
    r"(jam[oó]n(?:\s+de\s+cerdo)?|paleta(?:\s+de\s+cerdo)?|carne\s+de\s+(?:cerdo|pavo|pollo|vacuno)|"
    r"pechuga\s+de\s+(?:pavo|pollo)|lomo\s+de\s+cerdo)"
    r"[^0-9%,;.]{0,12}?[\(_\s]*(\d{1,3}(?:[.,]\d+)?)\s*_*\s*%",
    re.I)


def meat_pct(ingredients: str | None) -> Decimal | None:
    if not ingredients:
        return None
    m = _MEAT.search(ingredients)
    if not m:
        return None
    val = Decimal(m.group(2).replace(",", "."))
    if not 0 < val <= 100:
        return None
    return val
