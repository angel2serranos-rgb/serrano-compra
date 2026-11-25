"""Modo reconocimiento: descarga unas pocas fichas reales (respetando robots.txt y
con pausa entre peticiones) para ver CÓMO publica cada web sus precios.

Uso (lo lanza el workflow 'discover', a mano):
    python -m app.jobs.discover alcampo 8 ../discovery

Salida: discovery/<tienda>/*.html + informe.json. El workflow lo sube como
artefacto PRIVADO de la ejecución (no se publica en el repositorio).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from ..adapters.base import SourceBlocked
from ..adapters.extract import describe_page, extract_price
from ..adapters.stores import ADAPTER_CLASSES
from ..core.freshness import MADRID


def discover(store_id: str, n: int, out: Path, adapter=None) -> dict:
    adapter = adapter or ADAPTER_CLASSES[store_id](limit=max(n * 20, 50))
    report: dict = {"store": store_id, "at": datetime.now(MADRID).isoformat(), "pages": []}
    try:
        urls = adapter.product_urls()
    except SourceBlocked as e:
        report["blocked"] = str(e)
        return _save(report, out, store_id)
    report["sample_urls_found"] = len(urls)
    step = max(1, len(urls) // n) if urls else 1
    for url in urls[::step][:n]:
        entry: dict = {"url": url}
        try:
            html = adapter.client.get(url)
        except SourceBlocked as e:
            entry["blocked"] = str(e)
            report["pages"].append(entry)
            break                       # se para: no se insiste contra un bloqueo
        except Exception as e:          # noqa: BLE001 - se registra, no se oculta
            entry["error"] = repr(e)
            report["pages"].append(entry)
            continue
        fname = f"{adapter.external_id(url)}.html"
        (out / store_id).mkdir(parents=True, exist_ok=True)
        (out / store_id / fname).write_text(html, "utf-8")
        ex = extract_price(html, store_id=store_id, url=url)
        entry.update(file=fname, **describe_page(html),
                     generic_price=ex.price_text if ex else None,
                     strategy=ex.strategy if ex else None)
        report["pages"].append(entry)
    return _save(report, out, store_id)


def _save(report: dict, out: Path, store_id: str) -> dict:
    (out / store_id).mkdir(parents=True, exist_ok=True)
    (out / store_id / "informe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    return report


if __name__ == "__main__":
    sid = sys.argv[1]
    if sid not in ADAPTER_CLASSES:
        sys.exit(f"Supermercado no soportado: {sid!r}. Opciones: {sorted(ADAPTER_CLASSES)}")
    count = min(int(sys.argv[2]) if len(sys.argv) > 2 else 8, 15)
    dest = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("discovery")
    print(json.dumps(discover(sid, count, dest), ensure_ascii=False, indent=2))
