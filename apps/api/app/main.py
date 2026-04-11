from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import request_logging_middleware
from app.routers import admin_ai_routing, admin_connections, admin_semantic, auth, chat, dashboards

app = FastAPI(title="Smart BI API", version="0.1.0")
app.middleware("http")(request_logging_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin_connections.router)
app.include_router(admin_semantic.router)
app.include_router(admin_ai_routing.router)
app.include_router(chat.router)
app.include_router(dashboards.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
