from __future__ import annotations
from sqlalchemy import String, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models.wms.common import HasId, HasCreatedAt

class ProductionOrder(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_order"
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="RELEASED", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class ProductionMaterial(Base, HasId, HasCreatedAt):
    __tablename__ = "mes_production_material"
    prod_order_id: Mapped[str] = mapped_column(ForeignKey("mes_production_order.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    qty_required: Mapped[float] = mapped_column(String(32), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    prod_order: Mapped[ProductionOrder] = relationship()

Index("ix_mes_mat_po_item", ProductionMaterial.prod_order_id, ProductionMaterial.item_id)
