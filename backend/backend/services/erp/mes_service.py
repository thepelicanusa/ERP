from __future__ import annotations
from sqlalchemy.orm import Session

# Standalone stubs for MES integration. These allow the scan engine endpoints to execute without
# requiring a full MES module.
def start_operation(db: Session, mo_id: str, op_code: str, operator: str) -> dict:
    return {"status": "OK", "action": "START_OP", "mo_id": mo_id, "op_code": op_code, "operator": operator}

def issue_material(db: Session, mo_id: str, op_code: str, item_id: str, location_id: str, qty: float, operator: str) -> dict:
    return {"status": "OK", "action": "ISSUE", "mo_id": mo_id, "op_code": op_code, "item_id": item_id, "location_id": location_id, "qty": qty}

def receive_finished_goods(db: Session, mo_id: str, op_code: str, location_id: str, qty: float, operator: str) -> dict:
    return {"status": "OK", "action": "RECEIVE", "mo_id": mo_id, "op_code": op_code, "location_id": location_id, "qty": qty}

def record_qc(db: Session, mo_id: str, op_code: str, check_code: str, result: str, operator: str) -> dict:
    return {"status": "OK", "action": "QC", "mo_id": mo_id, "op_code": op_code, "check_code": check_code, "result": result}
