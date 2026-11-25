"""Tarea programada de actualización (la lanza GitHub Actions).

- Comprueba las fichas de `config/watchlist.json` de cada supermercado con lector validado.
- Guarda cada precio observado en data/prices/AAAA-MM-DD.json (histórico propio, con hora,
  fuente y URL) y un resumen por fuente en status/AAAA-MM-DD.json.
- Nunca marca 'actualizado' una fuente que no se ha podido consultar entera.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from ..adapters import ahorramas
from ..adapters.base import PoliteClient, SourceBlocked
from ..adapters.registry import STORES
from ..core.freshness import MADRID, SourceState
from ..core.units import Quantity
from ..core.validation import check_price

PARSERS = {"ahorramas": (ahorramas.parse, "https://www.ahorramas.com")}


def _family(name: str) -> str:
    n = name.lower()
    if "jam" in n and "cocido" in n:
        return "jamon_cocido"
    if any(w in n for w in ("tomate", "plátano", "platano", "aguacate", "pimiento", "banana")):
        return "fruta_verdura"
    return "default"


def check_store(store_id: str, urls: list[str], client=None) -> tuple[dict, list[dict]]:
    parse, base = PARSERS[store_id]
    client = client or PoliteClient(base)
    obs: list[dict] = []
    errors: list[str] = []
    blocked = False
    for url in urls:
        try:
            item = parse(client.get(url), url)
        except SourceBlocked as e:
            errors.append(str(e))
            blocked = True
            break                                 # no se insiste contra un bloqueo
        except Exception as e:                    # noqa: BLE001 - se registra
            errors.append(f"{url}: {e!r}")
            continue
        if item is None:
            errors.append(f"{url}: ficha sin datos fiables")
            continue
        if item.per_kg:
            pack = Quantity.parse(1, "kg")
        elif item.pack_g is not None:
            pack = Quantity.parse(item.pack_g, "g" if item.unit_label == "kg" else "ml")
        else:
            pack = Quantity.parse(1, "ud")
        chk = check_price(item.price, pack, family=_family(item.name),
                          shown_unit_price=None if item.per_kg else item.unit_price)
        rec = asdict(item)
        rec.update(store_id=store_id, url=url, kind="online_oficial",
                   observed_at=datetime.now(MADRID).isoformat(),
                   quarantine=not chk.ok, problems=list(chk.problems))
        rec["pack_g"] = None if item.pack_g is None else str(item.pack_g)
        rec["est_unit_g"] = None if item.est_unit_g is None else [str(x) for x in item.est_unit_g]
        obs.append(rec)
    if blocked and not obs:
        state = SourceState.DOWN
    elif errors:
        state = SourceState.PARTIAL
    else:
        state = SourceState.UPDATED_TODAY
    summary = {"state": state.value, "checked": len(obs), "expected": len(urls),
               "errors": errors, "coverage": "lista de seguimiento (no catálogo completo)"}
    return summary, obs


def run(slot: str, out_dir: Path, data_dir: Path, watchlist: dict) -> dict:
    started = datetime.now(MADRID)
    report = {"slot": slot, "started_at": started.isoformat(), "sources": {}}
    all_obs: list[dict] = []
    for sid, info in STORES.items():
        entry = {"name": info.name, "automated": info.automated, "coverage": info.coverage}
        urls = watchlist.get(sid, [])
        if not info.automated:
            entry.update(state=SourceState.PENDING.value, note=info.blocker or "sin lectura automática")
        elif sid not in PARSERS:
            entry.update(state=SourceState.PENDING.value, note="lector pendiente de validar")
        elif not urls:
            entry.update(state=SourceState.PENDING.value, note="lista de seguimiento vacía")
        else:
            summary, obs = check_store(sid, urls)
            entry.update(summary)
            all_obs += obs
        report["sources"][sid] = entry
    report["finished_at"] = datetime.now(MADRID).isoformat()
    day = started.date().isoformat()
    _append(out_dir / f"{day}.json", report)
    if all_obs:
        _append_many(data_dir / f"{day}.json", all_obs)
    return report


def _append(path: Path, item: dict) -> None:
    _append_many(path, [item])


def _append_many(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cur = json.loads(path.read_text("utf-8")) if path.exists() else []
    cur.extend(items)
    path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    slot = sys.argv[1] if len(sys.argv) > 1 else "manual"
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("..")
    wl = json.loads((root / "config" / "watchlist.json").read_text("utf-8"))
    r = run(slot, root / "status", root / "data" / "prices", wl)
    print(json.dumps(r, ensure_ascii=False, indent=2))
