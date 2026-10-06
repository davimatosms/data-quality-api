from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Check, CheckRuleResult, Source
from app.schemas import CheckCreate, CheckRead

router = APIRouter(prefix="/sources/{source_id}/checks", tags=["checks"])


@router.post("", response_model=CheckRead, status_code=201)
def create_check(source_id: int, payload: CheckCreate, db: Session = Depends(get_db)):
    if db.get(Source, source_id) is None:
        raise HTTPException(status_code=404, detail="Source not found")
    check = Check(
        source_id=source_id,
        checked_at=payload.checked_at,
        status=payload.status,
        metrics=payload.metrics,
        rule_results=[CheckRuleResult(**rule.model_dump()) for rule in payload.rule_results],
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check
