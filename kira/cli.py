"""CLI de Kira: inicializar, sembrar, conversar y servir."""

from __future__ import annotations

import argparse
import sys
from uuid import uuid4

from kira.agent.kira import build_agent
from kira.config import get_settings
from kira.db.migrate import init_databases
from kira.db.seed import seed_demo_data


def _cmd_init(_: argparse.Namespace) -> int:
    settings = get_settings()
    init_databases(settings)
    print(f"Bases inicializadas en {settings.db1_path} y {settings.db2_path}")
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    settings = get_settings()
    init_databases(settings)
    seeded = seed_demo_data(settings, force=args.force)
    print("Datos demo sembrados." if seeded else "La base ya tenía datos; usa --force para recrearlos.")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    settings = get_settings()
    init_databases(settings)
    agent = build_agent(
        session_id=args.session_id or f"cli-{uuid4().hex}",
        customer_id=args.customer_id or None,
        settings=settings,
    )
    result = agent(args.message)
    print(str(result).strip())
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    settings = get_settings()
    init_databases(settings)
    session_id = args.session_id or f"cli-{uuid4().hex}"
    agent = build_agent(
        session_id=session_id,
        customer_id=args.customer_id or None,
        settings=settings,
    )
    print(f"Kira lista. Sesión: {session_id}. Escribe 'salir' para terminar.")
    while True:
        try:
            message = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message.lower() in {"salir", "exit", "quit"}:
            break
        try:
            result = agent(message)
            print(f"Kira: {str(result).strip()}")
        except Exception as exc:  # noqa: BLE001 - CLI de demo
            print(f"Error: {exc}", file=sys.stderr)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    settings = get_settings()
    init_databases(settings)
    uvicorn.run(
        "kira.api.app:app",
        host=args.host or settings.api_host,
        port=args.port or settings.api_port,
        log_level=settings.log_level.lower(),
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kira", description="Agente Kira")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init-db", help="Crea las bases y siembra datos demo")
    init_parser.set_defaults(func=_cmd_init)

    seed_parser = sub.add_parser("seed", help="Siembra datos demo")
    seed_parser.add_argument("--force", action="store_true", help="Borra y recrea los datos de negocio")
    seed_parser.set_defaults(func=_cmd_seed)

    ask_parser = sub.add_parser("ask", help="Envía un mensaje y termina")
    ask_parser.add_argument("message")
    ask_parser.add_argument("--session-id", default="")
    ask_parser.add_argument("--customer-id", default="")
    ask_parser.set_defaults(func=_cmd_ask)

    chat_parser = sub.add_parser("chat", help="Conversación interactiva")
    chat_parser.add_argument("--session-id", default="")
    chat_parser.add_argument("--customer-id", default="")
    chat_parser.set_defaults(func=_cmd_chat)

    serve_parser = sub.add_parser("serve", help="Levanta la API FastAPI")
    serve_parser.add_argument("--host", default="")
    serve_parser.add_argument("--port", type=int, default=0)
    serve_parser.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
