from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_principal
from app.db.session import get_db
from app.events.bus import publish
from app.db.models.mdm import (
    MDMOrgUnit,
    MDMUoM,
    MDMItemClass,
    MDMItem,
    MDMParty,
    MDMPerson,
    MDMEquipment,
)

router = APIRouter(prefix="/mdm", tags=["mdm"])


def _require_admin(principal) -> None:
    roles = set(getattr(principal, "roles", None) or [])
    if "ADMIN" not in roles:
        raise HTTPException(403, "ADMIN role required")


# ---- Schemas ----
class UomIn(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=128)


class ItemClassIn(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=256)


class ItemIn(BaseModel):
    item_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=256)
    uom_code: str = Field(..., max_length=32)
    class_code: str | None = Field(default=None, max_length=64)
    status: str = "ACTIVE"
    revision: str = "A"


class PartyIn(BaseModel):
    party_type: str = Field(..., max_length=32)
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=256)


class OrgUnitIn(BaseModel):
    type: str = Field(..., max_length=32)  # ENTERPRISE|SITE|AREA|LINE|CELL
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=256)
    parent_id: str | None = None


class PersonIn(BaseModel):
    employee_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=256)
    email: str | None = Field(default=None, max_length=256)
    org_unit_id: str | None = None


class EquipmentIn(BaseModel):
    equipment_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=256)
    equipment_type: str = Field(default="GENERIC", max_length=64)
    org_unit_id: str | None = None


# ---- UoM ----
@router.get("/uoms")
def list_uoms(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(MDMUoM).order_by(MDMUoM.code.asc()).all()
    return [{"id": r.id, "code": r.code, "name": r.name} for r in rows]


@router.post("/uoms")
def create_uom(payload: UomIn, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    if db.query(MDMUoM).filter(MDMUoM.code == payload.code).first():
        raise HTTPException(409, "UoM code already exists")
    row = MDMUoM(code=payload.code, name=payload.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    publish(db, "mdm.uom.created", {"id": row.id, "code": row.code})
    return {"id": row.id, "code": row.code, "name": row.name}


# ---- Item Classes ----
@router.get("/item-classes")
def list_item_classes(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(MDMItemClass).order_by(MDMItemClass.code.asc()).all()
    return [{"id": r.id, "code": r.code, "name": r.name} for r in rows]


@router.post("/item-classes")
def create_item_class(payload: ItemClassIn, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    if db.query(MDMItemClass).filter(MDMItemClass.code == payload.code).first():
        raise HTTPException(409, "Item class code already exists")
    row = MDMItemClass(code=payload.code, name=payload.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    publish(db, "mdm.item_class.created", {"id": row.id, "code": row.code})
    return {"id": row.id, "code": row.code, "name": row.name}


# ---- Items ----
@router.get("/items")
def list_items(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(MDMItem).order_by(MDMItem.item_code.asc()).all()
    return [
        {
            "id": r.id,
            "item_code": r.item_code,
            "name": r.name,
            "uom_id": r.uom_id,
            "class_id": r.class_id,
            "status": r.status,
            "revision": r.revision,
        }
        for r in rows
    ]


@router.post("/items")
def create_item(payload: ItemIn, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    if db.query(MDMItem).filter(MDMItem.item_code == payload.item_code).first():
        raise HTTPException(409, "Item code already exists")

    uom = db.query(MDMUoM).filter(MDMUoM.code == payload.uom_code).first()
    if not uom:
        raise HTTPException(409, "Unknown uom_code")

    class_id = None
    if payload.class_code:
        ic = db.query(MDMItemClass).filter(MDMItemClass.code == payload.class_code).first()
        if not ic:
            raise HTTPException(409, "Unknown class_code")
        class_id = ic.id

    row = MDMItem(
        item_code=payload.item_code,
        name=payload.name,
        uom_id=uom.id,
        class_id=class_id,
        status=payload.status,
        revision=payload.revision,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    publish(db, "mdm.item.created", {"id": row.id, "item_code": row.item_code})
    return {
        "id": row.id,
        "item_code": row.item_code,
        "name": row.name,
        "uom_id": row.uom_id,
        "class_id": row.class_id,
        "status": row.status,
        "revision": row.revision,
    }


# ---- Parties ----
@router.get("/parties")
def list_parties(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(MDMParty).order_by(MDMParty.code.asc()).all()
    return [{"id": r.id, "party_type": r.party_type, "code": r.code, "name": r.name} for r in rows]


@router.post("/parties")
def create_party(payload: PartyIn, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    if db.query(MDMParty).filter(MDMParty.code == payload.code).first():
        raise HTTPException(409, "Party code already exists")
    row = MDMParty(party_type=payload.party_type, code=payload.code, name=payload.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    publish(db, "mdm.party.created", {"id": row.id, "code": row.code, "party_type": row.party_type})
    return {"id": row.id, "party_type": row.party_type, "code": row.code, "name": row.name}


# ---- Org Units (ISA-95 hierarchy) ----
@router.get("/org-units")
def list_org_units(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(MDMOrgUnit).order_by(MDMOrgUnit.type.asc(), MDMOrgUnit.code.asc()).all()
    return [
        {
            "id": r.id,
            "type": r.type,
            "code": r.code,
            "name": r.name,
            "parent_id": r.parent_id,
        }
        for r in rows
    ]


@router.post("/org-units")
def create_org_unit(payload: OrgUnitIn, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    if db.query(MDMOrgUnit).filter(MDMOrgUnit.type == payload.type, MDMOrgUnit.code == payload.code).first():
        raise HTTPException(409, "Org unit type+code already exists")
    if payload.parent_id:
        if not db.query(MDMOrgUnit).filter(MDMOrgUnit.id == payload.parent_id).first():
            raise HTTPException(409, "Unknown parent_id")
    row = MDMOrgUnit(type=payload.type, code=payload.code, name=payload.name, parent_id=payload.parent_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    publish(db, "mdm.org_unit.created", {"id": row.id, "type": row.type, "code": row.code})
    return {"id": row.id, "type": row.type, "code": row.code, "name": row.name, "parent_id": row.parent_id}


# ---- People ----
@router.get("/people")
def list_people(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(MDMPerson).order_by(MDMPerson.employee_code.asc()).all()
    return [
        {
            "id": r.id,
            "employee_code": r.employee_code,
            "name": r.name,
            "email": r.email,
            "org_unit_id": r.org_unit_id,
        }
        for r in rows
    ]


@router.post("/people")
def create_person(payload: PersonIn, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    if db.query(MDMPerson).filter(MDMPerson.employee_code == payload.employee_code).first():
        raise HTTPException(409, "employee_code already exists")
    if payload.org_unit_id and not db.query(MDMOrgUnit).filter(MDMOrgUnit.id == payload.org_unit_id).first():
        raise HTTPException(409, "Unknown org_unit_id")
    row = MDMPerson(employee_code=payload.employee_code, name=payload.name, email=payload.email, org_unit_id=payload.org_unit_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    publish(db, "mdm.person.created", {"id": row.id, "employee_code": row.employee_code})
    return {"id": row.id, "employee_code": row.employee_code, "name": row.name, "email": row.email, "org_unit_id": row.org_unit_id}


# ---- Equipment ----
@router.get("/equipment")
def list_equipment(db: Session = Depends(get_db), principal=Depends(get_principal)):
    rows = db.query(MDMEquipment).order_by(MDMEquipment.equipment_code.asc()).all()
    return [
        {
            "id": r.id,
            "equipment_code": r.equipment_code,
            "name": r.name,
            "equipment_type": r.equipment_type,
            "org_unit_id": r.org_unit_id,
        }
        for r in rows
    ]


@router.post("/equipment")
def create_equipment(payload: EquipmentIn, db: Session = Depends(get_db), principal=Depends(get_principal)):
    _require_admin(principal)
    if db.query(MDMEquipment).filter(MDMEquipment.equipment_code == payload.equipment_code).first():
        raise HTTPException(409, "equipment_code already exists")
    if payload.org_unit_id and not db.query(MDMOrgUnit).filter(MDMOrgUnit.id == payload.org_unit_id).first():
        raise HTTPException(409, "Unknown org_unit_id")
    row = MDMEquipment(
        equipment_code=payload.equipment_code,
        name=payload.name,
        equipment_type=payload.equipment_type,
        org_unit_id=payload.org_unit_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    publish(db, "mdm.equipment.created", {"id": row.id, "equipment_code": row.equipment_code})
    return {
        "id": row.id,
        "equipment_code": row.equipment_code,
        "name": row.name,
        "equipment_type": row.equipment_type,
        "org_unit_id": row.org_unit_id,
    }
