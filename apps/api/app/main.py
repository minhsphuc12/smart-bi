from fastapi import FastAPI

from app.core.logging import request_logging_middleware
from app.routers import admin_ai_routing, admin_connections, admin_semantic, auth, chat, dashboards

app = FastAPI(title="Smart BI API", version="0.1.0")
app.middleware("http")(request_logging_middleware)

app.include_router(auth.router)
app.include_router(admin_connections.router)
app.include_router(admin_semantic.router)
app.include_router(admin_ai_routing.router)
app.include_router(chat.router)
app.include_router(dashboards.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
