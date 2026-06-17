from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from database import get_db
from models import Supplier

router = APIRouter(prefix="/suppliers", tags=["供应商"])


class SupplierBody(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    remark: Optional[str] = None


@router.get("/")
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.name).all()


@router.post("/")
def create_supplier(body: SupplierBody, db: Session = Depends(get_db)):
    s = Supplier(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/{id}")
def update_supplier(id: int, body: SupplierBody, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{id}")
def delete_supplier(id: int, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    db.delete(s)
    db.commit()
    return {"ok": True}
