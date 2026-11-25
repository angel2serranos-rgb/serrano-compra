"""Tests de fuentes SIN red: sitemaps, extracción, ingredientes y plausibilidad.
HTML y XML son SIMULADOS; las URLs imitan el formato real visto el 25/11/2026."""
from decimal import Decimal

import pytest

from app.adapters.base import SourceBlocked
from app.adapters.extract import describe_page, extract_price
from app.adapters.sitemap import parse_sitemap
from app.adapters.stores import AhorramasAdapter, AlcampoAdapter
from app.core.ingredients import meat_pct
from app.core.units import Quantity
from app.core.validation import check_price, shrinkflation

INDEX = """<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://www.compraonline.alcampo.es/sitemaps/sitemap-categories-part1.xml</loc></sitemap>
<sitemap><loc>https://www.compraonline.alcampo.es/sitemaps/sitemap-products-part1.xml</loc></sitemap>
</sitemapindex>"""
PRODUCTS = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://www.compraonline.alcampo.es/products/helios-tomate-frito-570-g/29797</loc></url>
<url><loc>https://www.compraonline.alcampo.es/products/pimiento-italiano-al-peso/55210</loc></url>
<url><loc>https://www.compraonline.alcampo.es/recetas/no-es-producto</loc></url>
</urlset>"""


class FakeClient:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages

    def get(self, url: str) -> str:
        if url not in self.pages:
            raise SourceBlocked(f"simulado: {url}")
        return self.pages[url]


def test_sitemap_index_and_urls():
    children, urls = parse_sitemap(INDEX)
    assert len(children) == 2 and urls == []
    _, urls = parse_sitemap(PRODUCTS)
    assert len(urls) == 3


def test_alcampo_adapter_filters_products_and_ids():
    base = AlcampoAdapter.base_url
    client = FakeClient({
        base + "/sitemaps/sitemap_index.xml": INDEX,
        base + "/sitemaps/sitemap-products-part1.xml": PRODUCTS,
    })
    a = AlcampoAdapter(client=client)
    urls = a.product_urls()
    assert [a.external_id(u) for u in urls] == ["29797", "55210"]   # receta descartada


def test_ahorramas_id():
    a = AhorramasAdapter(client=FakeClient({}))
    assert a.external_id("https://www.ahorramas.com/jamon-cocido-extra-campofrio-1712.html") == "1712"
    with pytest.raises(ValueError):
        a.external_id("https://www.ahorramas.com/informacion")


def test_extraction_cascade():
    meta = '<meta property="product:price:amount" content="1.84"><p>Relacionado 0,99 €</p>'
    ex = extract_price(meta, store_id="t", url="u")
    assert ex.strategy == "meta" and ex.price_text == "1.84"
    # Solo texto con precios sueltos (como la ficha de prueba de Ahorramás): NO se adivina
    assert extract_price("<div>14,29€ 14,29€/Kg</div><div>Relacionado 2,99€</div>",
                         store_id="t", url="u") is None
    assert describe_page(meta)["has_meta_price"] is True


def test_adapter_returns_none_without_reliable_price():
    url = "https://www.ahorramas.com/jamon-cocido-extra-campofrio-1712.html"
    a = AhorramasAdapter(client=FakeClient({url: "<div>14,29€/Kg</div>"}))
    assert a.fetch_product(url) is None


@pytest.mark.parametrize("text,expected", [
    ("Jamón de cerdo _92%__, agua, sal y sal potásica, azúcar", Decimal(92)),   # formato OCU
    ("Jamón de cerdo (93 %), agua, sal", Decimal(93)),
    ("Ingredientes: paleta de cerdo 80%, agua", Decimal(80)),
    ("Pechuga de pavo 89,5%, agua, sal", Decimal("89.5")),
    ("Un jamón de cerdo, agua, sal, estabilizantes (E451, E452)", None),       # sin % → pendiente
    ("", None),
])
def test_meat_pct(text, expected):
    assert meat_pct(text) == expected


def test_plausibility_catches_published_errors():
    # 1 kg de jamón cocido a 1,85 € (error visto en un comparador de terceros)
    bad = check_price(185, Quantity.parse(1, "kg"), family="jamon_cocido")
    assert not bad.ok
    # leche 9,54 € el pack 6 x 1,5 l mostrada como 954 €/l
    milk = check_price(954, Quantity.parse(9, "l"), family="leche", shown_unit_price=95_400)
    assert not milk.ok and "≠ calculado" in milk.problems[0]
    # Dato coherente: 1,84 € / 570 g = 3,23 €/kg (ficha de Alcampo vista el 25/11/2026)
    assert check_price(184, Quantity.parse(570, "g"), shown_unit_price=323).ok
    assert not check_price(300, Quantity.parse(1, "l"), family="leche", previous=100).ok


def test_shrinkflation():
    assert shrinkflation(Quantity.parse(200, "g"), Quantity.parse(180, "g"), 250, 250) == Decimal("11.1")
    assert shrinkflation(Quantity.parse(200, "g"), Quantity.parse(200, "g"), 250, 260) is None


def test_discover_job_offline(tmp_path):
    import json

    from app.jobs.discover import discover
    base = AlcampoAdapter.base_url
    p1 = base + "/products/helios-tomate-frito-570-g/29797"
    client = FakeClient({
        base + "/sitemaps/sitemap_index.xml": INDEX,
        base + "/sitemaps/sitemap-products-part1.xml": PRODUCTS,
        p1: '<meta property="product:price:amount" content="1.84">',
    })   # la 2ª ficha no está → SourceBlocked simulado → el job se detiene y lo registra
    rep = discover("alcampo", 2, tmp_path, adapter=AlcampoAdapter(client=client))
    assert rep["pages"][0]["generic_price"] == "1.84"
    assert "blocked" in rep["pages"][1]
    saved = json.loads((tmp_path / "alcampo" / "informe.json").read_text("utf-8"))
    assert saved["sample_urls_found"] == 2
