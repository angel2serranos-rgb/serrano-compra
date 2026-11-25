"""Intérprete de listas de la compra en español (reglas, sin IA de pago).

Ejemplos que entiende:
  "1 kg de tomates pera"
  "cuatro aguacates"
  "200 g de jamón cocido con un mínimo del 93 % de carne"
  "detergente Ariel de cien lavados"
Lo que no entiende lo devuelve con `confidence` baja para que el usuario confirme.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal

from .units import Quantity

NUM_WORDS = {
    "un": 1, "una": 1, "uno": 1, "medio": Decimal("0.5"), "media": Decimal("0.5"),
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
    "nueve": 9, "diez": 10, "once": 11, "doce": 12, "docena": 12, "quince": 15,
    "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "cien": 100,
}
UNIT_WORDS = r"(kg|kilos?|kilogramos?|g|gr|gramos?|l|litros?|ml|cl|uds?|unidades?|lavados?)"
NUM = r"(\d+(?:[.,]\d+)?|" + "|".join(sorted(NUM_WORDS, key=len, reverse=True)) + r")"
FILLER = re.compile(r"^(quiero|necesito|compra(r)?|pon(me)?|añade|anade)\s+", re.I)


def _norm(s: str) -> str:
    return " ".join(s.strip().split())


def _num(tok: str) -> Decimal:
    tok = tok.lower()
    if tok in NUM_WORDS:
        return Decimal(str(NUM_WORDS[tok]))
    return Decimal(tok.replace(",", "."))


@dataclass
class ParsedLine:
    raw: str
    product: str
    quantity: Quantity | None
    brand: str | None = None
    min_attrs: dict[str, Decimal] = field(default_factory=dict)
    confidence: str = "alta"       # alta | media | baja


def parse_line(line: str, known_brands: set[str] | None = None) -> ParsedLine:
    raw = _norm(line)
    text = FILLER.sub("", raw)
    min_attrs: dict[str, Decimal] = {}

    m = re.search(r"(?:con\s+)?(?:un\s+)?m[ií]nimo\s+(?:del?\s+)?(\d+(?:[.,]\d+)?)\s*%\s*(?:de\s+)?(\w+)",
                  text, re.I)
    if m:
        key = {"carne": "meat_pct"}.get(m.group(2).lower(), f"{m.group(2).lower()}_pct")
        min_attrs[key] = _num(m.group(1))
        text = (text[:m.start()] + text[m.end():]).strip()

    qty = None
    # "<num> <unidad> de <producto>"
    m = re.match(rf"^{NUM}\s*{UNIT_WORDS}\.?\s+(?:de\s+)?(.+)$", text, re.I)
    if m:
        qty = Quantity.parse(_num(m.group(1)), m.group(2))
        text = m.group(3)
    else:
        # "<producto> de <num> <unidad>" (p. ej. detergente de cien lavados)
        m = re.match(rf"^(.+?)\s+de\s+{NUM}\s*{UNIT_WORDS}$", text, re.I)
        if m:
            qty = Quantity.parse(_num(m.group(2)), m.group(3))
            text = m.group(1)
        else:
            # "<num> <producto>" -> unidades
            m = re.match(rf"^{NUM}\s+(.+)$", text, re.I)
            if m:
                qty = Quantity.parse(_num(m.group(1)), "ud")
                text = m.group(2)

    brand = None
    if known_brands:
        folded = _fold(text)
        for b in sorted(known_brands, key=len, reverse=True):
            if _fold(b) in folded:
                brand = b
                break

    conf = "alta" if qty else "baja"
    return ParsedLine(raw, text.strip(" ,."), qty, brand, min_attrs, conf)


def parse_list(text: str, known_brands: set[str] | None = None) -> list[ParsedLine]:
    parts = re.split(r"[\n;]+|,\s*(?=\D)", text)
    return [parse_line(p, known_brands) for p in parts if p.strip()]


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
