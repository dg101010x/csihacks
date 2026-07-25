from __future__ import annotations

import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./relief_dev.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_all_tables() -> None:
    """Every module owns an independent DeclarativeBase (Section 29 — each
    stays independently pip-installable without a shared metadata registry),
    so apps/api is the one place that must know about all of them and
    create every table against the same engine."""
    from relief_audit.store import Base as AuditBase
    from relief_consumer_constitution.store import Base as ConstitutionBase
    from relief_ledger.sql import Base as LedgerBase
    from relief_obligations.store import Base as ObligationsBase
    from relief_workflow_worker.store import Base as WorkflowBase

    for base in (LedgerBase, ObligationsBase, ConstitutionBase, WorkflowBase, AuditBase):
        base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
