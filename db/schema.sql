-- Serrano Compra Inteligente PRO — esquema PostgreSQL (Neon free).
-- ESTADO: escrito, NO ejecutado aún (sin servidor PostgreSQL en el entorno de desarrollo).
-- Dinero: céntimos enteros. Fechas: timestamptz. Precios: append-only (trazabilidad).

CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- búsqueda tolerante a errores ortográficos

CREATE TABLE supermarket (
  id            text PRIMARY KEY,                 -- 'mercadona', 'alcampo'...
  name          text NOT NULL,
  website       text NOT NULL,
  enabled       boolean NOT NULL DEFAULT true,
  automated     boolean NOT NULL DEFAULT false
);

CREATE TABLE store (                               -- establecimiento físico
  id            bigserial PRIMARY KEY,
  supermarket_id text NOT NULL REFERENCES supermarket(id),
  name          text NOT NULL,
  postal_code   char(5) NOT NULL,
  lat           numeric(9,6), lon numeric(9,6),
  is_favorite   boolean NOT NULL DEFAULT false
);

CREATE TABLE category (
  id            serial PRIMARY KEY,
  parent_id     int REFERENCES category(id),
  name          text NOT NULL,
  UNIQUE (parent_id, name)
);

CREATE TABLE brand (
  id            serial PRIMARY KEY,
  name          text NOT NULL UNIQUE,
  private_label_of text REFERENCES supermarket(id) -- NULL = primera marca
);

CREATE TABLE product (                              -- producto tal como lo vende UNA cadena
  id            bigserial PRIMARY KEY,
  supermarket_id text NOT NULL REFERENCES supermarket(id),
  external_id   text NOT NULL,
  name          text NOT NULL,
  brand_id      int REFERENCES brand(id),
  category_id   int REFERENCES category(id),
  ean           varchar(14),
  pack_amount   numeric(12,3) NOT NULL CHECK (pack_amount > 0),
  pack_unit     text NOT NULL CHECK (pack_unit IN ('g','ml','ud','lavado')),
  per_kg        boolean NOT NULL DEFAULT false,
  drained_g     numeric(12,3),
  image_url     text,
  official_url  text,
  UNIQUE (supermarket_id, external_id)
);
CREATE INDEX product_ean_idx ON product (ean) WHERE ean IS NOT NULL;
CREATE INDEX product_name_trgm ON product USING gin (name gin_trgm_ops); -- requiere pg_trgm

CREATE TABLE product_attribute (                    -- % carne, azúcar, sal... con su fuente
  product_id    bigint NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  key           text NOT NULL,
  value         numeric(10,3) NOT NULL,
  source        text NOT NULL,                      -- 'ficha_oficial', 'openfoodfacts', 'manual'
  verified_at   timestamptz NOT NULL,
  PRIMARY KEY (product_id, key)
);

CREATE TABLE product_match (                        -- equivalencias entre cadenas
  a_id          bigint NOT NULL REFERENCES product(id),
  b_id          bigint NOT NULL REFERENCES product(id),
  kind          text NOT NULL CHECK (kind IN ('identico','equivalente','no_comparable')),
  method        text NOT NULL,                      -- 'ean', 'manual', 'sugerido'
  confirmed     boolean NOT NULL DEFAULT false,
  PRIMARY KEY (a_id, b_id),
  CHECK (a_id < b_id)
);

CREATE TABLE source_run (                           -- cada ejecución de cada fuente
  id            bigserial PRIMARY KEY,
  supermarket_id text NOT NULL REFERENCES supermarket(id),
  slot          text NOT NULL,
  started_at    timestamptz NOT NULL,
  finished_at   timestamptz,
  ok            boolean,
  products_checked int NOT NULL DEFAULT 0,
  products_expected int,
  prices_changed int NOT NULL DEFAULT 0,
  error         text
);
CREATE INDEX source_run_recent ON source_run (supermarket_id, started_at DESC);

CREATE TABLE price_observation (                    -- NUNCA se actualiza ni borra: histórico real
  id            bigserial PRIMARY KEY,
  product_id    bigint NOT NULL REFERENCES product(id),
  store_id      bigint REFERENCES store(id),
  postal_code   char(5),
  kind          text NOT NULL CHECK (kind IN ('online_oficial','tienda_verificado','folleto','ticket','estimado')),
  price_cents   int NOT NULL CHECK (price_cents >= 0),
  available     boolean,
  observed_at   timestamptz NOT NULL,
  source_run_id bigint REFERENCES source_run(id),
  evidence_url  text
);
CREATE INDEX price_obs_latest ON price_observation (product_id, observed_at DESC);

CREATE TABLE promotion (
  id            bigserial PRIMARY KEY,
  product_id    bigint NOT NULL REFERENCES product(id),
  type          text NOT NULL,
  n int, m int, pct numeric(5,2), price_cents int,
  channel       text NOT NULL DEFAULT 'ambos',
  requires_membership boolean NOT NULL DEFAULT false,
  valid_from    date NOT NULL,
  valid_to      date NOT NULL CHECK (valid_to >= valid_from),
  announced_only boolean NOT NULL DEFAULT false,    -- anunciada en folleto pero aún no activa
  conditions    text,
  source_run_id bigint REFERENCES source_run(id)
);
CREATE INDEX promotion_active ON promotion (product_id, valid_from, valid_to);

CREATE TABLE app_user (
  id            bigserial PRIMARY KEY,
  email         text NOT NULL UNIQUE,
  token_hash    text NOT NULL,                       -- nunca el token en claro
  postal_code   char(5) NOT NULL DEFAULT '28030',
  prefs         jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE basket (
  id            bigserial PRIMARY KEY,
  user_id       bigint NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  name          text NOT NULL,
  shopping_day  date,
  is_template   boolean NOT NULL DEFAULT false,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE basket_item (
  id            bigserial PRIMARY KEY,
  basket_id     bigint NOT NULL REFERENCES basket(id) ON DELETE CASCADE,
  label         text NOT NULL,
  amount        numeric(12,3) NOT NULL CHECK (amount > 0),
  unit          text NOT NULL,
  mandatory     boolean NOT NULL DEFAULT true,
  brands        text[],
  private_label_ok boolean NOT NULL DEFAULT true,
  min_attrs     jsonb NOT NULL DEFAULT '{}',
  locked_product_id bigint REFERENCES product(id),
  bought        boolean NOT NULL DEFAULT false
);

CREATE TABLE alert (
  id            bigserial PRIMARY KEY,
  user_id       bigint NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  product_id    bigint REFERENCES product(id),
  kind          text NOT NULL,                      -- bajada, promo, minimo_historico...
  target_cents  int,
  min_interval_hours int NOT NULL DEFAULT 24,
  last_sent_at  timestamptz
);

CREATE TABLE receipt (
  id            bigserial PRIMARY KEY,
  user_id       bigint NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  store_id      bigint REFERENCES store(id),
  purchased_at  timestamptz NOT NULL,
  total_cents   int NOT NULL,
  raw_ocr       text
);

CREATE TABLE audit_log (
  id            bigserial PRIMARY KEY,
  at            timestamptz NOT NULL DEFAULT now(),
  actor         text NOT NULL,
  action        text NOT NULL,
  detail        jsonb NOT NULL DEFAULT '{}'
);
