from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_frequency_minutes: Mapped[int] = mapped_column(Integer)
    freshness_tolerance: Mapped[float] = mapped_column(default=1.5)
    quality_rules: Mapped[list] = mapped_column(JSON, default=list)
    checks: Mapped[list["Check"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[Source] = relationship(back_populates="checks")
    rule_results: Mapped[list["CheckRuleResult"]] = relationship(
        back_populates="check", cascade="all, delete-orphan"
    )


class CheckRuleResult(Base):
    __tablename__ = "check_rule_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"), index=True)
    rule_name: Mapped[str] = mapped_column(String(120))
    passed: Mapped[bool]
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    check: Mapped[Check] = relationship(back_populates="rule_results")
