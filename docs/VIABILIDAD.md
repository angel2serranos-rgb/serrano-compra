# Matriz de viabilidad — 7 supermercados (25/11/2026)

Comprobado hoy con búsquedas web y lectura de cada `robots.txt`. **Pendiente en todos:**
leer las condiciones de uso completas y hacer una prueba real desde GitHub Actions (Fase 5).
Ningún supermercado de los 7 ofrece una API pública oficial de precios (no se ha encontrado ninguna).

| Supermercado | Fuente posible | robots.txt (hoy) | Obstáculo | Viabilidad | Plan |
|---|---|---|---|---|---|
| **Alcampo** | Web alcampo.es (+50.000 productos) | `User-agent: *` sin restricciones | Precio y stock distintos por tienda | **Alta (por probar)** | Adaptador 1 |
| **Ahorramás** | Fichas de ahorramas.com vía sitemap | Fichas permitidas; buscador AJAX y `/buscador?` prohibidos | Solo Madrid/CLM (es tu zona) | **Alta (por probar)** | Adaptador 2 |
| **Lidl** | Sitemap + folleto semanal | Prohibido `search?q=` y parámetros | Online casi sin alimentación | **Parcial** | Ofertas/folleto |
| **Aldi** | Sitemap + folleto | Prohibidas secciones concretas y filtros | Catálogo online limitado | **Parcial** | Ofertas/folleto |
| **Carrefour** | Fichas y categorías carrefour.es | Fichas permitidas; `/supermercado/ajax/*` prohibido | Cloudflare bloquea bots | **Baja desde la nube** | Probar; si bloquea → manual |
| **Mercadona** | API interna no oficial de tienda.mercadona.es | Nuestra herramienta fue **rechazada por robots.txt** | Uso no autorizado | **No automatizar** | Tickets + manual |
| **Costco** | sameday.costco.es (socios, vía Instacart) | — | Requiere sesión de socio | **No automatizar** | Tickets + manual |

## Datos clave
- Costco: online solo para socios, pedido mínimo 35 € + tarifa; afirma precios online = tienda.
- Carrefour: su buscador no tiene JSON público; las categorías sí tienen URL estable (`/catNNNNN/c`).
- GitHub Actions admite zona horaria en `schedule` desde marzo de 2026; puede retrasar ejecuciones.
- Las IPs de GitHub son de centro de datos: más probabilidad de bloqueo que una IP doméstica.

## Lo que esto significa (sin adornos)
- **Catálogo automático real esperado:** Alcampo y Ahorramás (si pasan la prueba), ofertas de Lidl y Aldi.
- **Mercadona y Costco** entrarán por tickets o a mano. Mercadona es la gran ausencia y conviene saberlo ya.
- Ningún catálogo se presentará como completo: cada fuente muestra su cobertura medida.
- Ingredientes, % de carne y alérgenos: ficha oficial cuando exista; Open Food Facts (base abierta) como apoyo, marcado como tal.

## Actualización 25/11/2026 22:15 — comprobación de fichas reales
- **Alcampo:** la tienda online está en `www.compraonline.alcampo.es` (otro dominio). Su robots.txt solo prohíbe login, cesta, entrega, pago y ordenaciones. Índice de sitemaps con 2 ficheros de productos. Ficha de prueba (Helios tomate frito 570 g): muestra **1,84 €**, **3,23 €/kg**, EAN e ingredientes. Cuadra: 1,84 / 0,570 = 3,228 → 3,23 €/kg.
- **Ahorramás:** sitemap de productos con fichas `/<nombre>-<id>.html`. En la ficha de prueba (jamón cocido extra Campofrío, al corte) **no hay JSON-LD**: el precio (14,29 €/kg, peso variable 100–250 g) va como texto. Necesita un lector propio, que solo se escribirá tras ver el HTML real.
- **Aviso de calidad:** muchos jamones "extra" del mercado declaran **92 %** de carne (etiquetas publicadas por OCU y en fichas de Alcampo). Con tu mínimo del 93 % quedarán excluidos: es lo correcto, pero la lista de candidatos será corta.
- **Comparadores de terceros también fallan:** se han visto publicados "1 kg de jamón a 1,85 €/kg" o leche a "954 €/l". Por eso cada precio pasa controles de plausibilidad antes de usarse.

## Prueba real desde GitHub Actions — 25/11/2026 22:40
| Supermercado | Resultado | Decisión |
|---|---|---|
| **Ahorramás** | 160 fichas listadas; **8 de 8** descargadas con precio en JSON-LD (p. ej. garbanzos Litoral 425 g: 2,15 €; yogur oveja Yaranza 140 g: 1,35 €) | ✅ Primera fuente automática real |
| **Alcampo** | Sitemap leído (160 fichas), pero la primera ficha devuelve **HTTP 403** | ⛔ Desactivado: no se insiste ni se disfraza el acceso. Queda por folleto/ticket |

Corrección: la nota anterior decía que la ficha de Ahorramás no tenía JSON-LD. Era una limitación de mi herramienta de lectura web, no de la página: desde GitHub sí aparece.
