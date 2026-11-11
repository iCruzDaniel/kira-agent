"""Datos demo de un negocio genérico: servicios, productos, recursos y FAQ."""

from __future__ import annotations

from kira.config import Settings
from kira.db.connection import read_connection, transaction
from kira.time_utils import now_iso

DEFAULT_SETTINGS = {
    "currency": "COP",
    "tax_rate": "0.19",
    "quote_valid_days": "7",
    "cancellation_hours": "24",
    "slot_step_minutes": "15",
    "delivery_fee_cents": "500000",
    "max_party_size": "12",
    "address": "Calle 123 #45-67, Bogotá",
    "phone": "+57 300 123 4567",
    "email": "hola@estudiokira.demo",
    "instagram": "@estudiokira.demo",
}

FAQ_ROWS = [
    (
        "¿Cuál es el horario de atención?",
        "Atendemos de lunes a viernes de 9:00 a 18:00 y los sábados de 9:00 a 14:00. "
        "Los domingos y festivos no hay atención.",
        "horario atencion abren cierran dias",
        "horario",
    ),
    (
        "¿Dónde están ubicados?",
        "Estamos en Calle 123 #45-67, Bogotá. Puedes llegar en TransMilenio o parquear en el "
        "parqueadero del edificio (sujeto a disponibilidad).",
        "direccion ubicacion donde llegar parqueadero",
        "ubicacion",
    ),
    (
        "¿Qué formas de pago aceptan?",
        "Aceptamos efectivo, tarjetas débito y crédito, y transferencias por Nequi o Daviplata. "
        "Para eventos pedimos un abono del 50%.",
        "pago pagar efectivo tarjeta nequi daviplata transferencia",
        "pagos",
    ),
    (
        "¿Puedo cancelar o reagendar mi cita?",
        "Sí. Puedes cancelar o reagendar sin costo hasta 24 horas antes de tu cita. "
        "Después de ese plazo se cobra el 50% del servicio.",
        "cancelar reagendar cambio cita politica",
        "politicas",
    ),
    (
        "¿Las cotizaciones tienen vigencia?",
        "Las cotizaciones tienen una vigencia de 7 días calendario. Si necesitas más tiempo, "
        "podemos generar una nueva cotización.",
        "cotizacion vigencia validez precio presupuesto",
        "cotizaciones",
    ),
    (
        "¿Hacen domicilios?",
        "Sí, entregamos productos a domicilio dentro de Bogotá. El costo depende de la zona y "
        "se confirma al crear el pedido.",
        "domicilio entrega envio pedido productos",
        "pedidos",
    ),
    (
        "¿Cuánto dura un corte de cabello?",
        "Un corte clásico dura aproximadamente 30 minutos. Corte + barba toma unos 45 minutos.",
        "duracion corte cabello tiempo",
        "servicios",
    ),
    (
        "¿Atienden eventos privados?",
        "Sí, contamos con una sala para eventos de hasta 12 personas. Podemos armar una "
        "cotización a medida según la fecha y el número de invitados.",
        "evento privado sala invitados celebracion",
        "eventos",
    ),
]


def _delete_demo_data(conn) -> None:
    for table in (
        "order_items",
        "orders",
        "bookings",
        "quote_items",
        "quotes",
        "faq",
        "service_resources",
        "business_hours",
        "services",
        "products",
        "resources",
        "categories",
        "settings",
    ):
        conn.execute(f"DELETE FROM {table}")


def _insert_demo_data(conn, settings: Settings) -> None:
    now = now_iso()

    values = {**DEFAULT_SETTINGS, "business_name": settings.business_name, "timezone": settings.timezone}
    conn.executemany(
        "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
        [(key, value, now) for key, value in values.items()],
    )

    categories = [
        ("Cortes", "Cortes de cabello y barba"),
        ("Color", "Coloración y tratamientos"),
        ("Barba", "Arreglo de barba"),
        ("Productos", "Productos para el cuidado personal"),
    ]
    conn.executemany(
        "INSERT INTO categories(name, description, active) VALUES (?, ?, 1)",
        categories,
    )
    category_ids = {
        row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM categories")
    }

    services = [
        (category_ids["Cortes"], "Corte clásico", "Corte con lavado y peinado", 30, 3_500_000),
        (category_ids["Cortes"], "Corte + barba", "Corte y perfilado de barba", 45, 5_000_000),
        (category_ids["Color"], "Color completo", "Coloración con tratamiento", 120, 12_000_000),
        (category_ids["Barba"], "Arreglo de barba", "Perfilado y aceite", 20, 2_000_000),
    ]
    conn.executemany(
        "INSERT INTO services(category_id, name, description, duration_minutes, price_cents, active) "
        "VALUES (?, ?, ?, ?, ?, 1)",
        services,
    )
    service_ids = {
        row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM services")
    }

    products = [
        (category_ids["Productos"], "Shampoo sólido", "Shampoo natural 80 g", 10, 4_500_000),
        (category_ids["Productos"], "Aceite para barba", "Aceite 30 ml", 10, 3_800_000),
        (category_ids["Productos"], "Cera mate", "Cera de fijación media", 10, 2_900_000),
    ]
    conn.executemany(
        "INSERT INTO products(category_id, name, description, prep_minutes, price_cents, active) "
        "VALUES (?, ?, ?, ?, ?, 1)",
        products,
    )

    resources = [
        ("Ana", "staff", 1, 1),
        ("Carlos", "staff", 1, 1),
        ("Sala principal", "room", 1, 12),
        ("Punto de recogida", "pickup", 2, 1),
    ]
    conn.executemany(
        "INSERT INTO resources(name, kind, capacity, seats, active) VALUES (?, ?, ?, ?, 1)",
        resources,
    )
    resource_ids = {
        row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM resources")
    }

    links = [
        (service_ids["Corte clásico"], resource_ids["Ana"]),
        (service_ids["Corte clásico"], resource_ids["Carlos"]),
        (service_ids["Corte + barba"], resource_ids["Ana"]),
        (service_ids["Corte + barba"], resource_ids["Carlos"]),
        (service_ids["Color completo"], resource_ids["Ana"]),
        (service_ids["Color completo"], resource_ids["Carlos"]),
        (service_ids["Arreglo de barba"], resource_ids["Ana"]),
        (service_ids["Arreglo de barba"], resource_ids["Carlos"]),
    ]
    conn.executemany(
        "INSERT INTO service_resources(service_id, resource_id) VALUES (?, ?)",
        links,
    )

    # Python weekday(): lunes=0 ... domingo=6
    hours = [
        (0, "09:00", "18:00"),
        (1, "09:00", "18:00"),
        (2, "09:00", "18:00"),
        (3, "09:00", "18:00"),
        (4, "09:00", "18:00"),
        (5, "09:00", "14:00"),
    ]
    conn.executemany(
        "INSERT INTO business_hours(weekday, open_time, close_time, active) VALUES (?, ?, ?, 1)",
        hours,
    )

    conn.executemany(
        "INSERT INTO faq(question, answer, keywords, category, active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 1, ?, ?)",
        [(*row, now, now) for row in FAQ_ROWS],
    )


def seed_if_empty(settings: Settings) -> bool:
    """Siembra datos demo solo cuando db_1 no tiene configuración."""

    with read_connection(settings.db1_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM settings").fetchone()["n"]
    if count:
        return False

    with transaction(settings.db1_path) as conn:
        _insert_demo_data(conn, settings)
    return True


def seed_demo_data(settings: Settings, force: bool = False) -> bool:
    """Siembra datos demo; con `force` borra y recrea el contenido de negocio."""

    with transaction(settings.db1_path) as conn:
        if force:
            _delete_demo_data(conn)
        else:
            count = conn.execute("SELECT COUNT(*) AS n FROM settings").fetchone()["n"]
            if count:
                return False
        _insert_demo_data(conn, settings)
    return True
