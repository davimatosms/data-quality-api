from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db import Base, engine
from app.routers import checks, sources

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Data Quality API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sources.router)
app.include_router(checks.router)


@app.get("/health", tags=["system"])
def health():
    from app.db import SessionLocal

    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
