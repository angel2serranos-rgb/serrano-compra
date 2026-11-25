"""Tests del núcleo. TODOS los precios aquí son SIMULADOS (inventados para probar
el cálculo); no representan precios reales de ningún supermercado."""
from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.adapters.jsonld import parse_product
from app.core.freshness import MADRID, SourceRun, SourceState, source_state
from app.core.models import BasketItem, Offer, PriceKind, StoreCosts
from app.core.money import fmt_eur, to_cents
from app.core.nlparse import parse_line
from app.core.optimizer import optimize
from app.core.promotions import Channel, Promotion, PromoType, cost_for_units
from app.core.units import Quantity, Unit, unit_price

DAY = date(2026, 11, 28)
NOW = datetime(2026, 11, 28, 9, 50, tzinfo=MADRID)
FRESH = datetime(2026, 11, 28, 6, 10, tzinfo=MADRID)


# ------------------------------------------------------------------ dinero

def test_money_parse_and_format():
    assert to_cents("1,99") == 199
    assert to_cents("1.234,56 €") == 123456
    assert to_cents("0.995") == 100          # half-up
    assert fmt_eur(123456) == "1.234,56 €"
    assert fmt_eur(-50) == "-0,50 €"
    with pytest.raises(TypeError):
        to_cents(1.99)                       # float prohibido


def test_unit_price():
    assert unit_price(299, Quantity.parse(200, "g")) == (1495, "€/kg")
    assert unit_price(1999, Quantity.parse(100, "lavados")) == (20, "€/lavado")
    assert unit_price(105, Quantity.parse(1, "l")) == (105, "€/l")


# ------------------------------------------------------------------ promociones

def P(t, **kw):
    return Promotion(t, date(2026, 11, 1), date(2026, 11, 30), **kw)


@pytest.mark.parametrize("promo,units,expected", [
    (P(PromoType.N_FOR_M, n=3, m=2), 3, 200),
    (P(PromoType.N_FOR_M, n=3, m=2), 4, 300),
    (P(PromoType.N_FOR_M, n=2, m=1), 2, 100),
    (P(PromoType.NTH_UNIT_PCT, n=2, pct=Decimal(50)), 2, 150),
    (P(PromoType.NTH_UNIT_PCT, n=2, pct=Decimal(70)), 2, 130),
    (P(PromoType.NTH_UNIT_PCT, n=2, pct=Decimal(70)), 3, 230),
    (P(PromoType.DIRECT_PCT, pct=Decimal(20)), 2, 160),
    (P(PromoType.QTY_PRICE, n=3, price=80), 2, 200),
    (P(PromoType.QTY_PRICE, n=3, price=80), 3, 240),
])
def test_promotions(promo, units, expected):
    assert cost_for_units(100, units, promo, DAY).pay_now == expected


def test_promo_rules():
    expired = Promotion(PromoType.N_FOR_M, date(2026, 10, 1), date(2026, 10, 31), n=2, m=1)
    assert cost_for_units(100, 2, expired, DAY).pay_now == 200
    member = P(PromoType.DIRECT_PCT, pct=Decimal(50), requires_membership=True)
    assert cost_for_units(100, 1, member, DAY).pay_now == 100           # no verificado
    assert cost_for_units(100, 1, member, DAY, user_eligible=True).pay_now == 50
    online_only = P(PromoType.DIRECT_PCT, pct=Decimal(50), channel=Channel.ONLINE)
    assert cost_for_units(100, 1, online_only, DAY, channel=Channel.STORE).pay_now == 100
    bal = cost_for_units(1000, 1, P(PromoType.FUTURE_BALANCE_PCT, pct=Decimal(10)), DAY)
    assert (bal.pay_now, bal.future_balance) == (1000, 100)            # saldo ≠ ahorro hoy


# ------------------------------------------------------------------ frescura

def test_source_state_never_lies():
    ok_today = SourceRun(FRESH, FRESH, True, 100, 100)
    failed = SourceRun(FRESH, FRESH, False, 0, 100, "HTTP 403")
    yesterday = FRESH - timedelta(days=1)
    assert source_state(ok_today, FRESH, NOW) == SourceState.UPDATED_TODAY
    assert source_state(failed, yesterday, NOW) == SourceState.DOWN
    assert source_state(failed, FRESH, NOW) == SourceState.PARTIAL
    assert source_state(None, yesterday, NOW) == SourceState.STALE
    assert source_state(SourceRun(FRESH, FRESH, True, 60, 100), FRESH, NOW) == SourceState.PARTIAL
    assert source_state(None, None, NOW) == SourceState.PENDING


def test_dst_change_is_safe():
    # 25/10/2026 cambio de hora en España: 03:00 -> 02:00
    before = datetime(2026, 10, 25, 1, 30, tzinfo=MADRID)
    after = datetime(2026, 10, 25, 9, 0, tzinfo=MADRID)
    assert source_state(SourceRun(before, before, True, 1, 1), before, after) \
        == SourceState.UPDATED_TODAY


# ------------------------------------------------------------------ lenguaje natural

def test_nlparse_acceptance_basket():
    a = parse_line("Quiero un kilo de tomates pera")
    assert a.quantity == Quantity(Decimal(1000), Unit.G) and a.product == "tomates pera"
    b = parse_line("cuatro aguacates")
    assert b.quantity == Quantity(Decimal(4), Unit.UD)
    c = parse_line("200 g de jamón cocido con un mínimo del 93 % de carne")
    assert c.quantity == Quantity(Decimal(200), Unit.G)
    assert c.min_attrs == {"meat_pct": Decimal(93)} and c.product == "jamón cocido"
    d = parse_line("Detergente Ariel de cien lavados", known_brands={"Ariel"})
    assert d.quantity == Quantity(Decimal(100), Unit.LAVADO) and d.brand == "Ariel"
    assert parse_line("leche").confidence == "baja"


# ------------------------------------------------------------------ optimizador

def offer(store, pid, price, qty, unit, **kw):
    kw.setdefault("observed_at", FRESH)
    kw.setdefault("kind", PriceKind.ONLINE)
    return Offer(store, pid, pid, kw.pop("brand", "X"), price, Quantity.parse(qty, unit), **kw)


ITEMS = [
    BasketItem("tomate", "1 kg tomate pera", Quantity.parse(1, "kg")),
    BasketItem("platano", "1 kg plátano Canarias", Quantity.parse(1, "kg")),
    BasketItem("aguacate", "4 aguacates", Quantity.parse(4, "ud")),
    BasketItem("jamon", "200 g jamón ≥93 % carne", Quantity.parse(200, "g"),
               min_attrs={"meat_pct": Decimal(93)}),
]

# SIMULADO
OFFERS = {
    "tomate": [offer("A", "tomA", 199, 1, "kg", per_kg=True),
               offer("B", "tomB", 179, 1, "kg", per_kg=True),
               offer("C", "tomC", 230, 1, "kg", per_kg=True)],
    "platano": [offer("A", "plaA", 249, 1, "kg", per_kg=True),
                offer("B", "plaB", 269, 1, "kg", per_kg=True),
                offer("C", "plaC", 210, 1, "kg", per_kg=True)],
    "aguacate": [offer("A", "agA", 399, 1, "kg", per_kg=True,
                       est_unit_g=(Decimal(180), Decimal(250))),
                 offer("B", "agB", 299, 3, "ud"),
                 offer("C", "agC", 349, 4, "ud")],
    "jamon": [offer("A", "jamA65", 150, 200, "g", attrs={"meat_pct": Decimal(65)}),  # barato pero NO cumple
              offer("A", "jamA93", 289, 200, "g", attrs={"meat_pct": Decimal(93)}),
              offer("B", "jamB??", 199, 200, "g"),                                   # % sin verificar
              offer("C", "jamC95", 310, 200, "g", attrs={"meat_pct": Decimal(95)})],
}
STORES = {s: StoreCosts(s, travel=100) for s in "ABC"}


def test_quality_rules_exclude_cheap_and_unverified_ham():
    r = optimize(ITEMS, OFFERS, STORES, max_stores=3, day=DAY, now=NOW)
    reasons = {(e.product_id, e.reason) for e in r.exclusions}
    assert ("jamA65", "meat_pct=65 inferior al mínimo 93") in reasons
    assert ("jamB??", "meat_pct sin verificar (pendiente)") in reasons
    for plan in r.best_by_size.values():
        assert plan.assignment["jamon"].offer.product_id in {"jamA93", "jamC95"}


def test_store_b_cannot_complete_basket_alone():
    r = optimize(ITEMS, OFFERS, {"B": STORES["B"]}, max_stores=1, day=DAY, now=NOW)
    assert r.chosen is None and r.best_incomplete.missing == ["jamon"]


def test_estimated_weight_is_flagged_and_ranged():
    r = optimize(ITEMS, OFFERS, {"A": STORES["A"]}, max_stores=1, day=DAY, now=NOW)
    q = r.chosen.assignment["aguacate"]
    assert q.estimated and q.cost_low == 287 and q.cost_high == 399   # 4×180 g / 4×250 g a 3,99 €/kg
    assert r.chosen.has_estimates


def test_leftover_from_big_pack():
    r = optimize(ITEMS, OFFERS, {"B": STORES["B"]}, max_stores=1, day=DAY, now=NOW)
    q = r.best_incomplete.assignment["aguacate"]
    assert q.packs == 2 and q.leftover == 2 and q.cost == 598


def test_stale_prices_excluded():
    old = {k: [o.__class__(**{**o.__dict__, "observed_at": FRESH - timedelta(days=3)})
               for o in v] for k, v in OFFERS.items()}
    r = optimize(ITEMS, old, STORES, max_stores=3, day=DAY, now=NOW)
    assert r.chosen is None and all(e.reason == "precio caducado" for e in r.exclusions)


def test_threshold_prevents_pointless_extra_trip():
    r_free = optimize(ITEMS, OFFERS, STORES, max_stores=3, day=DAY, now=NOW)
    r_thr = optimize(ITEMS, OFFERS, STORES, max_stores=3, day=DAY, now=NOW,
                     min_saving_per_extra_store=10_000)
    assert len(r_thr.chosen.stores) == 1
    assert r_free.chosen.total <= r_thr.chosen.total


def test_optimizer_matches_independent_brute_force():
    """Verificación independiente: prueba TODAS las asignaciones producto→tienda."""
    r = optimize(ITEMS, OFFERS, STORES, max_stores=3, day=DAY, now=NOW)
    # costes por (item, tienda) calculados a mano para los válidos:
    cost = {
        "tomate": {"A": 199, "B": 179, "C": 230},
        "platano": {"A": 249, "B": 269, "C": 210},
        "aguacate": {"A": 343, "B": 598, "C": 349},  # A: 4×215 g×3,99 = 343,14 → 343
        "jamon": {"A": 289, "C": 310},
    }
    best = None
    for combo in itertools.product(*[sorted(cost[i]) for i in cost]):
        stores_used = set(combo)
        total = sum(cost[i][s] for i, s in zip(cost, combo)) + 100 * len(stores_used)
        best = total if best is None else min(best, total)
    assert r.chosen.total == best


def test_online_minimum_order_and_fees():
    online = {s: StoreCosts(s, delivery_fee=500, min_order=1500) for s in "ABC"}
    r = optimize(ITEMS, OFFERS, online, max_stores=2, day=DAY, now=NOW, channel=Channel.ONLINE)
    assert 2 not in r.best_by_size          # ninguna pareja llega al mínimo en ambas tiendas
    assert r.best_by_size.get(1) is None    # y ninguna tienda sola llega a 15 €


# ------------------------------------------------------------------ adaptador JSON-LD

def test_jsonld_parser_fixture():
    with open("tests/fixtures/product_jsonld_SIMULADO.html", encoding="utf-8") as fh:
        html = fh.read()
    p = parse_product(html, store_id="test", url="https://ejemplo.invalid/p/1")
    assert p.name == "Leche semidesnatada 1 L" and p.price_text == "0.99"
    assert p.ean == "0000000000000" and p.available is True and p.brand == "MarcaEjemplo"
    assert parse_product("<html></html>", store_id="t", url="u") is None
