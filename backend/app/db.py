"""Small persistent catalog and job store; SQLite locally or PostgreSQL/PostGIS."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class Region(Base):
    __tablename__ = "regions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    bounds: Mapped[list] = mapped_column(JSON)


class Provenance(Base):
    __tablename__ = "dataset_provenance"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    details: Mapped[dict] = mapped_column(JSON)


class Scene(Base):
    __tablename__ = "scenes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_provenance.id"))
    details: Mapped[dict] = mapped_column(JSON)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    details: Mapped[dict] = mapped_column(JSON)


class Analysis(Base):
    __tablename__ = "analysis_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"))
    model_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"))
    status: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    error: Mapped[str | None] = mapped_column(String, nullable=True)


class Result(Base):
    __tablename__ = "analysis_results"
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), primary_key=True)
    details: Mapped[dict] = mapped_column(JSON)


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
Session = sessionmaker(engine, expire_on_commit=False)
