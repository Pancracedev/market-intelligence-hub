from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import SessionLocal
from .routers import auth, digests, watchers
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

app.include_router(auth.router)
app.include_router(watchers.router)
app.include_router(watchers.runs_router)
app.include_router(digests.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
