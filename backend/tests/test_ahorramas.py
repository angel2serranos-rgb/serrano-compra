"""Lector de Ahorramás. Las fichas son RECONSTRUIDAS: JSON-LD y textos copiados del
formato observado en fichas reales el 25/11/2026 (no son las páginas completas)."""
from decimal import Decimal

from app.adapters.ahorramas import parse


def page(name, sku, price, brand, visible):
    return f"""<html><head><script type="application/ld+json">
{{"@context":"http://schema.org/","@type":"Product","name":"{name}","sku":"{sku}",
"brand":{{"@type":"Brand","name":"{brand}"}},
"offers":{{"@type":"Offer","priceCurrency":"EUR","price":"{price}",
"availability":"http://schema.org/InStock"}}}}</script></head>
<body><nav>Otros ingredientes para reposter&iacute;a</nav>{visible}
<div>Te puede interesar... Producto X 9 ,99&euro; 1.0 Kg --> 0,99&euro;/Kg</div></body></html>"""


def test_fixed_pack_ham():
    html = page("Jamón cocido en lonchas calidad extra Delizias Noel 120g", "22464", "2.39", "NOEL",
                "Jam&oacute;n cocido en lonchas calidad extra Delizias Noel 120g 2 ,39&euro; "
                "1.0 Kg --> 19,92&euro;/KILO A&ntilde;adir a la cesta")
    it = parse(html, "https://www.ahorramas.com/x-22464.html")
    assert (it.price, it.unit_price, it.per_kg, it.pack_g) == (239, 1992, False, Decimal(120))


def test_variable_weight_ham_is_per_kg():
    html = page("Jamón cocido extra Campofrío", "1712", "14.29", "CAMPOFRIO",
                "Jam&oacute;n cocido extra Campofr&iacute;o 14 ,29&euro; 1.0 Kg --> 14,29&euro;/Kg "
                "Peso 100 gr 100 gr 150 gr 200 gr 250 gr OPCI&Oacute;N DE PREPARACI&Oacute;N")
    it = parse(html, "u")
    assert it.per_kg and it.price == 1429 and it.pack_g is None and it.est_unit_g is None


def test_piece_with_approx_weight():
    html = page("Aguacate", "52808", "5.99", "",
                "Aguacate 5 ,99&euro; 1.0 Kg --> 5,99&euro;/Kg Peso Unidades 300 gr 300 gr 600 gr "
                "900 gr 1200 gr Peso aprox unidad 300 gr")
    it = parse(html, "u")
    assert it.per_kg and it.est_unit_g == (Decimal(255), Decimal(345))


def test_mismatch_between_jsonld_and_text_gives_nothing():
    html = page("Tomate pera", "14086", "2.69", "",
                "Tomate pera 2 ,79&euro; 1.0 Kg --> 2,79&euro;/Kg Peso Unidades 200 gr")
    assert parse(html, "u") is None


def test_name_quantity_contradiction_gives_nothing():
    # dice 120g pero precio/€kg implica 200 g → no se publica
    html = page("Jamón Prueba 120g", "1", "2.00", "X",
                "Jam&oacute;n Prueba 120g 2 ,00&euro; 1.0 Kg --> 10,00&euro;/KILO")
    assert parse(html, "u") is None


def test_check_store_offline():
    from app.adapters.base import SourceBlocked
    from app.jobs.run_update import check_store

    ok = "https://www.ahorramas.com/aguacate-52808.html"
    bad = "https://www.ahorramas.com/roto-1.html"
    pages = {ok: page("Aguacate", "52808", "5.99", "",
                      "Aguacate 5 ,99&euro; 1.0 Kg --> 5,99&euro;/Kg Peso Unidades 300 gr "
                      "Peso aprox unidad 300 gr"),
             bad: "<html>sin datos</html>"}

    class C:
        def get(self, url):
            if url not in pages:
                raise SourceBlocked("403 simulado")
            return pages[url]

    summary, obs = check_store("ahorramas", [ok, bad], client=C())
    assert summary["state"] == "Actualización parcial" and summary["checked"] == 1
    assert obs[0]["per_kg"] and obs[0]["price"] == 599 and not obs[0]["quarantine"]
    summary, obs = check_store("ahorramas", ["https://www.ahorramas.com/x-9.html"], client=C())
    assert summary["state"] == "Fuente temporalmente no disponible" and obs == []
