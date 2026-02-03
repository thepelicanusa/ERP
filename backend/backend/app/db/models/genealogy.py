from __future__ import annotations
from sqlalchemy import String, ForeignKey, Numeric, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from app.db.base import Base
from app.db.models.common import HasId, HasCreatedAt

class GenealogyLink(Base, HasId, HasCreatedAt):
    __tablename__ = "inv_genealogy_link"
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    production_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    consumed_txn_id: Mapped[str] = mapped_column(ForeignKey("wms_inventory_txn.id"), nullable=False, index=True)
    produced_txn_id: Mapped[str] = mapped_column(ForeignKey("wms_inventory_txn.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18,6), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

Index("ix_genealogy_po", GenealogyLink.production_order_id)
Index("ix_genealogy_consumed", GenealogyLink.consumed_txn_id)
Index("ix_genealogy_produced", GenealogyLink.produced_txn_id)
