"""Adaptadores concretos. Datos verificados el 25/11/2026 (ver docs/VIABILIDAD.md):

- Alcampo: tienda online en www.compraonline.alcampo.es; índice de sitemaps en
  /sitemaps/sitemap_index.xml con sitemap-products-part1/2. Fichas tipo
  /products/<slug>/<id>; muestran precio, €/kg, EAN e ingredientes.
- Ahorramás: índice /sitemap_index.xml con sitemap_0-product.xml. Fichas tipo
  /<slug>-<id>.html. Los frescos al corte son "PESO VARIABLE" con precio €/kg.
  Reconocimiento real 25/11/2026 desde GitHub: 8/8 fichas con JSON-LD Product y precio.
- Alcampo: reconocimiento real 25/11/2026 → sitemap OK, fichas HTTP 403. Desactivado.

El parseo definitivo de cada web se escribe DESPUÉS de ver su HTML real con el
modo reconocimiento (app/jobs/discover.py). Hasta entonces, solo la cascada genérica.
"""
from __future__ import annotations

import re

from .base import PoliteClient, RawProduct, StoreAdapter
from .extract import extract_price
from .sitemap import parse_sitemap


class SitemapAdapter(StoreAdapter):
    sitemap_index: str
    product_sitemap_hint: str      # subcadena que identifica los sitemaps de producto
    id_pattern: re.Pattern

    def __init__(self, client: PoliteClient | None = None, limit: int | None = None):
        self.client = client or PoliteClient(self.base_url)
        self.limit = limit

    def product_urls(self) -> list[str]:
        self.sitemap_sample: list[str] = []          # para el informe si nada encaja
        urls: list[str] = []
        pending = [self.sitemap_index]
        seen = 0
        while pending and seen < 40:                 # tope de sitemaps leídos por pase
            sm = pending.pop(0)
            seen += 1
            children, locs = parse_sitemap(self.client.get(sm))
            pending += [c for c in children if self.product_sitemap_hint in c]
            if len(self.sitemap_sample) < 15:
                self.sitemap_sample += locs[: 15 - len(self.sitemap_sample)]
            urls.extend(u for u in locs if self.id_pattern.search(u))
            if self.limit and len(urls) >= self.limit:
                return urls[: self.limit]
        return urls

    def external_id(self, url: str) -> str:
        m = self.id_pattern.search(url)
        if not m:
            raise ValueError(f"URL sin id reconocible: {url}")
        return m.group(1)

    def fetch_product(self, url: str) -> RawProduct | None:
        html = self.client.get(url)
        ex = extract_price(html, store_id=self.store_id, url=url)
        if ex is None:
            return None
        return RawProduct(self.store_id, self.external_id(url), ex.name or "", url,
                          ex.price_text, "EUR", ex.brand, ex.ean, None, ex.available,
                          extra={"strategy": ex.strategy})


class AlcampoAdapter(SitemapAdapter):
    store_id = "alcampo"
    name = "Alcampo"
    base_url = "https://www.compraonline.alcampo.es"
    sitemap_index = base_url + "/sitemaps/sitemap_index.xml"
    product_sitemap_hint = "sitemap-products"
    id_pattern = re.compile(r"/products/[^/]+/(\d+)/?$")
    coverage_note = "Precio online de la ubicación por defecto; puede variar por tienda"


class AhorramasAdapter(SitemapAdapter):
    store_id = "ahorramas"
    name = "Ahorramás"
    base_url = "https://www.ahorramas.com"
    sitemap_index = base_url + "/sitemap_index.xml"
    product_sitemap_hint = "-product"
    id_pattern = re.compile(r"-(\d+)\.html$")
    coverage_note = "Precio online; frescos al corte con precio €/kg"


class CarrefourAdapter(SitemapAdapter):
    """Sitemap de alimentación declarado en su robots.txt. Fichas /supermercado/.../R-<id>/p."""
    store_id = "carrefour"
    name = "Carrefour"
    base_url = "https://www.carrefour.es"
    sitemap_index = base_url + "/crs/cdn-static/sitemap-food/index.xml"
    product_sitemap_hint = ""
    id_pattern = re.compile(r"/R-([A-Za-z0-9-]+)/p/?$")


class LidlAdapter(SitemapAdapter):
    """Sitemap declarado en robots.txt. Patrón de ficha por confirmar en reconocimiento."""
    store_id = "lidl"
    name = "Lidl"
    base_url = "https://www.lidl.es"
    sitemap_index = base_url + "/static/sitemap.xml"
    product_sitemap_hint = ""
    id_pattern = re.compile(r"/p(\d{5,})/?$")


class AldiAdapter(SitemapAdapter):
    """Sitemap declarado en robots.txt. Patrón de ficha por confirmar en reconocimiento."""
    store_id = "aldi"
    name = "Aldi"
    base_url = "https://www.aldi.es"
    sitemap_index = base_url + "/.aldi-nord-sitemap.xml"
    product_sitemap_hint = ""
    id_pattern = re.compile(r"-(\d{6,})\.html$")


ADAPTER_CLASSES = {c.store_id: c for c in (AlcampoAdapter, AhorramasAdapter, CarrefourAdapter,
                                           LidlAdapter, AldiAdapter)}
