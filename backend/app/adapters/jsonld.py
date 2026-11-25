"""Extrae datos de producto de JSON-LD schema.org (Product/Offer) embebido en la ficha.

Es un estándar público que muchas tiendas incluyen para buscadores. Si una web no lo
trae, este parser devuelve None: NO se rellena nada a ojo.
PENDIENTE: validar con fichas reales de cada supermercado (Fase 5).
"""
from __future__ import annotations

import json
import re
from typing import Any

from .base import RawProduct

_SCRIPT = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                     re.DOTALL | re.IGNORECASE)


def _walk(node: Any):
    if isinstance(node, list):
        for n in node:
            yield from _walk(n)
    elif isinstance(node, dict):
        yield node
        for key in ("@graph", "itemListElement"):
            if key in node:
                yield from _walk(node[key])


def _is_product(n: dict) -> bool:
    t = n.get("@type")
    return t == "Product" or (isinstance(t, list) and "Product" in t)


def parse_product(html: str, *, store_id: str, url: str) -> RawProduct | None:
    for block in _SCRIPT.findall(html):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for node in _walk(data):
            if not _is_product(node):
                continue
            offers = node.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            brand = node.get("brand")
            if isinstance(brand, dict):
                brand = brand.get("name")
            image = node.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            avail = offers.get("availability")
            price = offers.get("price")
            return RawProduct(
                store_id=store_id,
                external_id=str(node.get("sku") or node.get("productID") or url),
                name=str(node.get("name", "")).strip(),
                url=url,
                price_text=str(price) if price is not None else None,
                currency=offers.get("priceCurrency"),
                brand=brand,
                ean=node.get("gtin13") or node.get("gtin") or node.get("gtin8"),
                image_url=image,
                available=None if avail is None else str(avail).endswith("InStock"),
            )
    return None
