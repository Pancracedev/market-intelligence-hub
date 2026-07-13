import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import SessionLocal
from .routers import auth, comparison_groups, digests, watchers
from .seed import ensure_demo_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_demo_user(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Market Intelligence Hub API",
    description="Multi-tenant API for the competitive intelligence platform.",
    version="0.2.0",
    lifespan=lifespan,
)

cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(watchers.router)
app.include_router(watchers.runs_router)
app.include_router(digests.router)
app.include_router(comparison_groups.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
