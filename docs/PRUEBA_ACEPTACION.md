# Prueba real de aceptación — Ahorramás (25/11/2026 22:50)

Precios **reales** leídos automáticamente desde GitHub Actions en ahorramas.com (precio **online**; en tienda física puede variar). Fuente: `data/prices/2026-11-25.json`.

| Producto pedido | Ficha elegida | Precio leído | Coste calculado |
|---|---|---|---|
| 1 kg tomate pera | Tomate pera | 2,69 €/kg | **2,69 €** |
| 1 kg plátano de Canarias | Plátano Canario bandeja | 3,19 € (3,19 €/kg → bandeja de 1 kg, *deducido*) | **3,19 €** |
| 4 aguacates | Aguacate | 5,99 €/kg; "peso aprox. unidad 300 g" | **7,19 € ESTIMADO** (6,11–8,27 € con ±15 % *supuesto*) |
| 200 g jamón cocido ≥ 93 % carne | — | La web no publica el % de carne | **PENDIENTE** |

**Resultado con tu regla del 93 %:** cesta **INCOMPLETA** (falta el jamón). Subtotal del resto: **13,07 €**.

**Sin exigir el 93 % (solo como referencia):** jamón cocido extra Campofrío al corte, 200 g × 14,29 €/kg = 2,86 € → total **15,93 €**. Otras opciones: Alipende 180 g a 1,84 € (10,22 €/kg; harían falta 2 envases = 3,68 €, sobran 160 g) y Noel Delizias 120 g a 2,39 € (19,92 €/kg).

Cálculos comprobados: 2,39 / 0,120 = 19,92 €/kg · 1,84 / 0,180 = 10,22 €/kg · 4 × 0,300 kg × 5,99 = 7,188 → 7,19 €.

## Lo que falta para completar la prueba
- **% de carne:** buscar la etiqueta por otra vía permitida (Open Food Facts por EAN, foto de la etiqueta o introducción manual).
- **Otros 6 supermercados:** Alcampo bloquea (403); Mercadona y Costco sin lectura automática; Carrefour, Lidl y Aldi pendientes de probar.
