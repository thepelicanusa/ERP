from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class Task(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_task"
    type: Mapped[str] = mapped_column(String(24), nullable=False)  # RECEIVE|PUTAWAY|PICK|PACK|COUNT
    status: Mapped[str] = mapped_column(String(24), default="READY", nullable=False)  # READY|IN_PROGRESS|DONE|EXCEPTION
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # link to source doc
    source_type: Mapped[str | None] = mapped_column(String(24), nullable=True)  # RECEIPT|ORDER|COUNT
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class TaskStep(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_task_step"
    task_id: Mapped[str] = mapped_column(ForeignKey("wms_task.id"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # SCAN_LOCATION|SCAN_ITEM|SCAN_LOT|ENTER_QTY|CONFIRM
    prompt: Mapped[str] = mapped_column(String(256), nullable=False)
    expected: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # e.g. {location_code: "..."}
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)  # PENDING|DONE
    captured: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    task: Mapped[Task] = relationship()

Index("ix_task_steps_task_seq", TaskStep.task_id, TaskStep.seq, unique=True)

class TaskException(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_task_exception"
    task_id: Mapped[str] = mapped_column(ForeignKey("wms_task.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped[Task] = relationship()
