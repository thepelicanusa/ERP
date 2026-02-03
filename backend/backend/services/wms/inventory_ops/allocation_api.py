from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_principal
from services.wms.inventory_ops.allocation_service import allocate_order

router = APIRouter(prefix="/allocations", tags=["allocations"])

@router.post("/orders/{order_id}")
def allocate(order_id: str, db: Session = Depends(get_db), p=Depends(get_principal)):
    try:
        return allocate_order(db, order_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
