"""Short, actionable API messages for common SQLAlchemy / driver connectivity errors."""

from sqlalchemy.exc import SQLAlchemyError


def humanize_sqlalchemy_error(exc: SQLAlchemyError, *, prefix: str) -> str:
    """
    Map frequent driver errors to guidance without dumping full stack traces.

    ``prefix`` is a short label such as ``Query failed`` or ``Connection failed``.
    """
    text = str(exc).strip()
    lowered = text.lower()
    if "password authentication failed" in lowered:
        return (
            f"{prefix}: PostgreSQL rejected the username/password. "
            "Update this datasource in Admin → Connections. "
            "For `docker compose` in this repo, defaults are host `localhost`, port `5432`, "
            "database `smartbi`, user `smartbi`, password `smartbi` "
            "(see `apps/api/data/connections.example.json`)."
        )
    if "could not connect to server" in lowered or "connection refused" in lowered:
        return (
            f"{prefix}: could not reach the database host/port. "
            "Confirm the server is running and Admin → Connections host/port are correct."
        )
    if "timeout" in lowered and "connect" in lowered:
        return (
            f"{prefix}: connection timed out. Check network, firewall, and host/port."
        )
    return f"{prefix}: {text}"
