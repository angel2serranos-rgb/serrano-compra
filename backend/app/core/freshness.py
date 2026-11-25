"""Caducidad de datos y estado de fuentes. Nunca se muestra un dato viejo como actual."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


class SourceState(str, Enum):
    UPDATED_TODAY = "Actualizado hoy"
    RUNNING = "Actualización en curso"
    PARTIAL = "Actualización parcial"
    PENDING = "Pendiente de actualizar"
    STALE = "Datos antiguos"
    DOWN = "Fuente temporalmente no disponible"


def is_fresh(observed_at: datetime, now: datetime, max_age: timedelta) -> bool:
    if observed_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("Fechas sin zona horaria: prohibido (riesgo de error en cambio de hora)")
    return now - observed_at <= max_age


@dataclass(frozen=True)
class SourceRun:
    started_at: datetime
    finished_at: datetime | None
    ok: bool
    products_checked: int
    products_expected: int | None     # None = cobertura desconocida (no se presume completa)
    error: str = ""


def source_state(last_run: SourceRun | None, last_ok: datetime | None, now: datetime) -> SourceState:
    """Estado mostrado al usuario. Regla: si falló, NO es 'actualizado'."""
    today = now.astimezone(MADRID).date()
    if last_run is not None and last_run.finished_at is None:
        return SourceState.RUNNING
    if last_run is not None and not last_run.ok:
        if last_ok and last_ok.astimezone(MADRID).date() == today:
            return SourceState.PARTIAL
        return SourceState.DOWN
    if last_ok is None:
        return SourceState.PENDING
    if last_ok.astimezone(MADRID).date() != today:
        return SourceState.STALE
    if last_run and last_run.products_expected and last_run.products_checked < last_run.products_expected:
        return SourceState.PARTIAL
    return SourceState.UPDATED_TODAY
