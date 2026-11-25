"""Contrato común de los adaptadores de supermercado + cliente HTTP respetuoso.

Reglas del cliente (no negociables):
- Consulta robots.txt y NO pide URLs prohibidas.
- Una petición cada `min_interval` segundos como mínimo (por defecto 3 s).
- No elude CAPTCHA, login ni bloqueos: si recibe 403/429/captcha, para y lo registra.
- User-Agent identificable, sin hacerse pasar por un navegador.
"""
from __future__ import annotations

import time
import urllib.request
import urllib.robotparser
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from ..core.freshness import MADRID

USER_AGENT = "SerranoCompraBot/0.1 (uso personal no comercial)"


class SourceBlocked(Exception):
    """La fuente no permite el acceso (robots, 403, 429, captcha). No se reintenta a la fuerza."""


@dataclass
class RawProduct:
    """Lo que devuelve un adaptador. Campos ausentes = None (nunca inventados)."""
    store_id: str
    external_id: str
    name: str
    url: str
    price_text: str | None
    currency: str | None
    brand: str | None = None
    ean: str | None = None
    image_url: str | None = None
    available: bool | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(MADRID))
    extra: dict = field(default_factory=dict)


class PoliteClient:
    def __init__(self, base_url: str, min_interval: float = 3.0, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.min_interval = min_interval
        self.timeout = timeout
        self._last = 0.0
        self._robots = urllib.robotparser.RobotFileParser(self.base_url + "/robots.txt")
        self._robots_loaded = False

    def allowed(self, url: str) -> bool:
        if not self._robots_loaded:
            self._robots.read()
            self._robots_loaded = True
        return self._robots.can_fetch(USER_AGENT, url)

    def get(self, url: str) -> str:
        if urlparse(url).netloc != urlparse(self.base_url).netloc:
            raise ValueError("URL fuera del dominio del adaptador")
        if not self.allowed(url):
            raise SourceBlocked(f"robots.txt prohíbe {url}")
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept-Language": "es-ES"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise SourceBlocked(f"HTTP {e.code} en {url}") from e
            raise
        finally:
            self._last = time.monotonic()
        if "captcha" in body.lower()[:5000]:
            raise SourceBlocked(f"CAPTCHA detectado en {url}: se detiene sin eludirlo")
        return body


class StoreAdapter(ABC):
    store_id: str
    name: str
    base_url: str
    enabled: bool = True
    coverage_note: str = ""

    @abstractmethod
    def product_urls(self) -> list[str]:
        """URLs de producto permitidas (normalmente desde el sitemap oficial)."""

    @abstractmethod
    def fetch_product(self, url: str) -> RawProduct | None:
        """Descarga y parsea una ficha. None si no hay datos fiables."""
