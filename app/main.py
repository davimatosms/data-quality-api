from fastapi import FastAPI
from sqlalchemy import text

from app.db import Base, engine
from app.routers import checks, sources

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Data Quality API", version="0.1.0")
app.include_router(sources.router)
app.include_router(checks.router)


@app.get("/health", tags=["system"])
def health():
    from app.db import SessionLocal

    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
