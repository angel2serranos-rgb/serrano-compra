# Serrano Compra Inteligente PRO — v0.2 (Fase 1–2 + inicio Fase 5)

Comparador y optimizador de la compra para Madrid (CP 28030). Coste: **0 €**.

## Estado real (25/11/2026)

| Pieza | Estado |
|---|---|
| Matriz de viabilidad (`docs/VIABILIDAD.md`) | ✅ Hecha (pendiente: condiciones de uso y prueba real desde la nube) |
| Núcleo: dinero, unidades, promociones, frescura, optimizador, lenguaje natural | ✅ Hecho y **probado** (41 tests pasan) |
| Caso `/compare` (esquemas + servicio) | ✅ Probado sin servidor |
| API FastAPI (`app/api/main.py`) | ⚠️ Escrita, **no ejecutada** (FastAPI no instalado en el entorno de desarrollo) |
| Esquema PostgreSQL (`db/schema.sql`) | ⚠️ Escrito, **no ejecutado** |
| Tarea programada + workflow | ✅ Job probado en local · ⚠️ workflow sin probar en GitHub |
| Adaptadores Alcampo y Ahorramás | ⏳ Lectura de sitemap + cascada de extracción probadas **sin red**; falta ver su HTML real |
| Modo reconocimiento (`discover.yml`) | ⚠️ Escrito y probado sin red; primera ejecución real en tu GitHub |
| % de carne desde ingredientes, controles de plausibilidad, reducflación | ✅ Probado |
| Frontend PWA, alertas, tickets, histórico visual | ⏳ Fases siguientes |

**Ningún precio de este repositorio es real.** Los tests usan datos simulados y lo dicen.

## Arquitectura (0 €)
```
GitHub Actions (8 pases/día, hora Madrid) ──► adaptadores ──► Neon PostgreSQL (gratis, 1 GB)
                                                                   ▲
PWA (Vercel / GitHub Pages) ──► API FastAPI (Vercel Hobby) ────────┘
```

## Probar en tu PC (Windows)
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q                                   # deben pasar todos
set API_TOKEN=pon-aqui-un-token-largo
uvicorn app.api.main:app --reload           # http://127.0.0.1:8000/api/docs
```

## Puesta en marcha en GitHub (gratis)
1. Crear repositorio **público** y subir esta carpeta.
2. Crear base de datos en neon.tech (plan Free, sin tarjeta) y guardar `DATABASE_URL` en *Settings → Secrets → Actions*.
3. Actions → `update-prices` → *Run workflow* para la primera prueba. El registro queda en `status/`.

Secretos: nunca en el código. Ver `.env.example`.
