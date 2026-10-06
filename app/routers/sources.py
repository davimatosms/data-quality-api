from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Check, Source
from app.schemas import SourceCreate, SourceRead, SourceSummary, StatusRead
from app.services.freshness import freshness_status

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceRead, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.put("/{source_id}", response_model=SourceRead)
def update_source(source_id: int, payload: SourceCreate, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    for key, value in payload.model_dump().items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()


@router.get("", response_model=list[SourceSummary])
def list_sources(db: Session = Depends(get_db)):
    sources = list(db.scalars(select(Source).order_by(Source.id)))
    summaries = []
    for source in sources:
        latest = db.scalars(
            select(Check)
            .where(Check.source_id == source.id)
            .order_by(Check.checked_at.desc())
            .limit(1)
        ).first()
        summaries.append(
            {
                **{field: getattr(source, field) for field in (
                    "id", "name", "description", "expected_frequency_minutes",
                    "freshness_tolerance", "quality_rules",
                )},
                "freshness": freshness_status(source, latest.checked_at if latest else None),
                "quality": latest.status if latest else "UNKNOWN",
            }
        )
    return summaries


@router.get("/{source_id}/status", response_model=StatusRead)
def get_status(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    checks = list(
        db.scalars(
            select(Check)
            .where(Check.source_id == source_id)
            .order_by(Check.checked_at.desc())
            .limit(10)
        )
    )
    latest = checks[0] if checks else None
    return {
        "source_id": source_id,
        "freshness": freshness_status(source, latest.checked_at if latest else None),
        "quality": latest.status if latest else "UNKNOWN",
        "latest_check": latest,
        "history": checks,
    }
