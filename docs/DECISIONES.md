# Registro de decisiones técnicas

| # | Fecha | Decisión | Motivo |
|---|---|---|---|
| 1 | 25/11/2026 | Coste 0 €: GitHub Actions + Neon (PostgreSQL, 1 GB gratis) + Vercel Hobby (API) | Requisito del usuario. Vercel Hobby es gratis para uso personal no comercial |
| 2 | 25/11/2026 | Descartado Supabase | El plan gratis pausa el proyecto tras 1 semana de poca actividad |
| 3 | 25/11/2026 | Descartado Oracle Always Free como principal | Recorte de límites sin aviso (agosto 2026) y recuperación de instancias inactivas |
| 4 | 25/11/2026 | Dinero en céntimos `int`; `float` prohibido (lanza error) | Exactitud |
| 5 | 25/11/2026 | Optimizador por enumeración exacta de combinaciones | 7 cadenas = 127 combinaciones: exacto, rápido y verificable; sin IA |
| 6 | 25/11/2026 | Requisito sin verificar (p. ej. % carne ausente) = producto excluido | Principio "no recomendar lo que incumple" |
| 7 | 25/11/2026 | Cliente HTTP respeta robots.txt, 1 petición/3 s, se detiene ante 403/429/CAPTCHA | No eludir restricciones |
| 8 | 25/11/2026 | Mercadona y Costco sin lectura automática | robots/autenticación; ver VIABILIDAD.md |
| 9 | 25/11/2026 | Horarios a :07/:37/:52 en vez de en punto | GitHub retrasa o descarta más las ejecuciones en punto |
| 10 | 25/11/2026 | El job guarda un registro diario en `status/` (commit) | Registro verificable + evita la pausa de 60 días en repos públicos |
| 11 | 25/11/2026 | Asistente MiniYO por reglas (nlparse) | 0 € y cálculos fuera de cualquier modelo de lenguaje |
