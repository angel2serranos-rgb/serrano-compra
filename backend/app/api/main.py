"""API HTTP (FastAPI). Estos endpoints son de NUESTRA app, no APIs de los supermercados.

Estado: escrito pero NO ejecutado en el entorno de desarrollo (FastAPI no estaba
instalado). Ejecutar `pytest` + `uvicorn app.api.main:app` en local para validarlo.

Fase actual: endpoints sin estado. Cestas, favoritos, alertas, etc. llegan con la
base de datos (Fase 3), con autenticación por token.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from ..adapters.registry import STORES
from .schemas import CompareIn, CompareOut
from .service import compare

API_TOKEN = os.environ.get("API_TOKEN", "")          # obligatorio en producción
ALLOWED_ORIGINS = [o for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o]

app = FastAPI(title="Serrano Compra Inteligente PRO API", version="0.1.0",
              docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type"])


def require_token(authorization: str = Header(default="")) -> None:
    if not API_TOKEN:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "API_TOKEN no configurado")
    expected = f"Bearer {API_TOKEN}"
    if not secrets.compare_digest(authorization.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/supermarkets", dependencies=[Depends(require_token)])
def supermarkets() -> list[dict]:
    return [s.__dict__ for s in STORES.values()]


@app.post("/api/v1/compare", response_model=CompareOut, dependencies=[Depends(require_token)])
def compare_endpoint(req: CompareIn) -> CompareOut:
    try:
        return compare(req)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
