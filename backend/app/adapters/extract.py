"""Extracción de precio desde una ficha HTML en cascada, de más fiable a menos.

1. JSON-LD schema.org Product  (estándar, fiable)
2. Metadatos de producto: <meta property="product:price:amount"> / itemprop="price"
3. Selectores propios del supermercado (se añaden SOLO tras ver HTML real: Fase 5)

Si ninguna estrategia funciona, devuelve None. Nunca se coge "el primer precio
que aparezca" porque en las fichas hay precios de productos relacionados.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .jsonld import parse_product

_META_PRICE = re.compile(
    r'<meta[^>]+(?:property|name|itemprop)=["\'](?:product:price:amount|og:price:amount|price)["\']'
    r'[^>]*content=["\']([0-9]+(?:[.,][0-9]{1,2})?)["\']', re.I)
_META_PRICE_REV = re.compile(
    r'<meta[^>]+content=["\']([0-9]+(?:[.,][0-9]{1,2})?)["\'][^>]*'
    r'(?:property|name|itemprop)=["\'](?:product:price:amount|og:price:amount|price)["\']', re.I)
_ITEMPROP = re.compile(r'itemprop=["\']price["\'][^>]*content=["\']([0-9]+(?:[.,][0-9]{1,2})?)["\']',
                       re.I)


@dataclass(frozen=True)
class Extraction:
    strategy: str            # 'jsonld' | 'meta' | 'itemprop'
    price_text: str
    name: str | None = None
    brand: str | None = None
    ean: str | None = None
    available: bool | None = None


def extract_price(html: str, *, store_id: str, url: str) -> Extraction | None:
    p = parse_product(html, store_id=store_id, url=url)
    if p and p.price_text:
        return Extraction("jsonld", p.price_text, p.name, p.brand, p.ean, p.available)
    for rx, name in ((_META_PRICE, "meta"), (_META_PRICE_REV, "meta"), (_ITEMPROP, "itemprop")):
        m = rx.search(html)
        if m:
            return Extraction(name, m.group(1))
    return None


def describe_page(html: str) -> dict:
    """Informe para el modo reconocimiento: qué datos estructurados trae la ficha."""
    low = html.lower()
    return {
        "bytes": len(html),
        "has_jsonld": "application/ld+json" in low,
        "has_jsonld_product": bool(re.search(r'"@type"\s*:\s*"product"', low)),
        "has_meta_price": bool(_META_PRICE.search(html) or _META_PRICE_REV.search(html)),
        "has_itemprop_price": bool(_ITEMPROP.search(html)),
        "has_next_data": "__next_data__" in low,
        "has_initial_state": "__initial_state__" in low or "__preloaded_state__" in low,
        "looks_like_captcha": "captcha" in low[:5000],
    }
