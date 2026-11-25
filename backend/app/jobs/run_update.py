"""Tarea programada de actualización (la lanza GitHub Actions).

Escribe un registro verificable en status/AAAA-MM-DD.json con lo que ha pasado
en cada supermercado. Nunca marca 'actualizado' una fuente que no se ha consultado.

Fase actual: aún no hay adaptadores validados contra webs reales, así que todas
las fuentes salen como 'Pendiente de actualizar'. Es el comportamiento correcto.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from ..adapters.registry import STORES
from ..core.freshness import MADRID, SourceState

ADAPTERS: dict = {}   # store_id -> StoreAdapter validado (se rellena en Fase 5)


def run(slot: str, out_dir: Path) -> dict:
    started = datetime.now(MADRID)
    report = {"slot": slot, "started_at": started.isoformat(), "sources": {}}
    for sid, info in STORES.items():
        entry = {"name": info.name, "automated": info.automated, "coverage": info.coverage}
        adapter = ADAPTERS.get(sid)
        if not info.automated:
            entry.update(state=SourceState.PENDING.value, note=info.blocker or "sin lectura automática")
        elif adapter is None:
            entry.update(state=SourceState.PENDING.value, note="adaptador pendiente de validar")
        else:  # pragma: no cover - Fase 5
            entry.update(_run_adapter(adapter))
        report["sources"][sid] = entry
    report["finished_at"] = datetime.now(MADRID).isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{started.date().isoformat()}.json"
    runs = json.loads(path.read_text("utf-8")) if path.exists() else []
    runs.append(report)
    path.write_text(json.dumps(runs, ensure_ascii=False, indent=2), "utf-8")
    return report


def _run_adapter(adapter) -> dict:  # pragma: no cover - Fase 5
    raise NotImplementedError


if __name__ == "__main__":
    slot = sys.argv[1] if len(sys.argv) > 1 else "manual"
    r = run(slot, Path(sys.argv[2]) if len(sys.argv) > 2 else Path("status"))
    print(json.dumps(r, ensure_ascii=False, indent=2))
