"""Catálogo de los 7 supermercados y su estado de viabilidad (ver docs/VIABILIDAD.md).

`automated=False` significa que NO hay lectura automática aprobada todavía:
sus precios solo entran por folleto, ticket o introducción manual.
Añadir un supermercado nuevo = añadir una entrada aquí + su adaptador. Nada más.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoreInfo:
    id: str
    name: str
    website: str
    automated: bool
    channels: tuple[str, ...]          # fuentes previstas
    coverage: str                      # cobertura real esperada, sin adornos
    blocker: str = ""


STORES: dict[str, StoreInfo] = {s.id: s for s in [
    StoreInfo("ahorramas", "Ahorramás", "https://www.ahorramas.com", True,
              ("online_oficial",),
              "Funciona desde GitHub: 8/8 fichas con precio JSON-LD (25/11/2026)"),
    StoreInfo("alcampo", "Alcampo", "https://www.compraonline.alcampo.es", False,
              ("folleto", "ticket", "manual"),
              "Sitemap legible; fichas bloqueadas desde GitHub (HTTP 403, 25/11/2026)",
              "HTTP 403 desde servidores de GitHub: no se insiste ni se disfraza el acceso"),
    StoreInfo("carrefour", "Carrefour", "https://www.carrefour.es", False,
              ("online_oficial",), "Fichas permitidas por robots, pero protegidas contra bots",
              "Protección anti-bots: probable bloqueo desde GitHub Actions"),
    StoreInfo("mercadona", "Mercadona", "https://tienda.mercadona.es", False,
              ("ticket", "manual"), "Solo tickets/manual hasta verificar condiciones",
              "API interna no oficial; nuestro acceso de prueba fue rechazado por robots.txt"),
    StoreInfo("lidl", "Lidl", "https://www.lidl.es", True,
              ("folleto", "online_oficial"), "Parcial: ofertas y folleto, no catálogo completo"),
    StoreInfo("aldi", "Aldi", "https://www.aldi.es", True,
              ("folleto", "online_oficial"), "Parcial: ofertas y folleto, no catálogo completo"),
    StoreInfo("costco", "Costco", "https://www.costco.es", False,
              ("ticket", "manual"), "Solo tickets/manual",
              "Compra online solo para socios con sesión iniciada: no se automatiza"),
]}
