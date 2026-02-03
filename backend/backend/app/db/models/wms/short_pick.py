from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class ShortPick(Base, HasId, HasCreatedAt):
    __tablename__ = "wms_short_pick"
    order_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requested_qty: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)
    picked_qty: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)
    remaining_qty: Mapped[float] = mapped_column(Numeric(18,6), nullable=False)
    resolution: Mapped[str | None] = mapped_column(String(24), nullable=True)  # REALLOCATE|BACKORDER|CANCEL
