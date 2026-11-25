"""Lectura de sitemaps XML (índices y listas de URLs). Solo stdlib."""
from __future__ import annotations

import xml.etree.ElementTree as ET

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    """Devuelve (sitemaps_hijos, urls). Tolera sitemaps sin namespace."""
    root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    tag = root.tag.replace(NS, "")
    locs = [el.text.strip() for el in root.iter() if el.tag.replace(NS, "") == "loc" and el.text]
    if tag == "sitemapindex":
        return locs, []
    return [], locs
