-- db_1: datos de negocio de Kira
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_faq_active ON faq(active);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER REFERENCES categories(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    price_cents INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER REFERENCES categories(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    prep_minutes INTEGER NOT NULL DEFAULT 15,
    price_cents INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('staff', 'room', 'pickup')),
    capacity INTEGER NOT NULL DEFAULT 1,
    seats INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS service_resources (
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    PRIMARY KEY (service_id, resource_id)
);

CREATE TABLE IF NOT EXISTS business_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    open_time TEXT NOT NULL,
    close_time TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_business_hours_weekday ON business_hours(weekday, active);

CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'accepted', 'expired', 'cancelled')),
    currency TEXT NOT NULL,
    subtotal_cents INTEGER NOT NULL,
    tax_cents INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quote_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK (item_type IN ('service', 'product')),
    item_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    line_total_cents INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quote_items_quote ON quote_items(quote_id);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('appointment', 'event', 'order')),
    customer_id TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL DEFAULT '',
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    service_id INTEGER REFERENCES services(id),
    party_size INTEGER NOT NULL DEFAULT 1,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('confirmed', 'cancelled', 'completed', 'no_show')),
    notes TEXT NOT NULL DEFAULT '',
    quote_id INTEGER REFERENCES quotes(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_resource_time
    ON bookings(resource_id, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_start ON bookings(start_at);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT NOT NULL UNIQUE,
    booking_id INTEGER NOT NULL REFERENCES bookings(id),
    quote_id INTEGER REFERENCES quotes(id),
    customer_id TEXT NOT NULL DEFAULT '',
    fulfillment TEXT NOT NULL DEFAULT 'pickup' CHECK (fulfillment IN ('pickup', 'delivery')),
    delivery_address TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('pending', 'confirmed', 'ready', 'completed', 'cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK (item_type IN ('service', 'product')),
    item_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    line_total_cents INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
