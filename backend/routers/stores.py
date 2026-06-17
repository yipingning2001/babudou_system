from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
from auth import require_owner

router = APIRouter(prefix="/stores", tags=["门店"])


class StoreCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None


class StoreOut(BaseModel):
    id: int
    name: str
    address: Optional[str]
    phone: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=list[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    return db.query(models.Store).all()


@router.post("/", response_model=StoreOut)
def create_store(store: StoreCreate, db: Session = Depends(get_db), _owner: models.User = Depends(require_owner)):
    db_store = models.Store(**store.model_dump())
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.put("/{store_id}", response_model=StoreOut)
def update_store(store_id: int, store: StoreCreate, db: Session = Depends(get_db), _owner: models.User = Depends(require_owner)):
    db_store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not db_store:
        raise HTTPException(status_code=404, detail="门店不存在")
    for key, value in store.model_dump().items():
        setattr(db_store, key, value)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.delete("/{store_id}")
def delete_store(store_id: int, db: Session = Depends(get_db), _owner: models.User = Depends(require_owner)):
    db_store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not db_store:
        raise HTTPException(status_code=404, detail="门店不存在")

    order_count = db.query(models.Order).filter(models.Order.store_id == store_id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该门店已有 {order_count} 笔订单记录，不能删除（会破坏历史数据）。",
        )
    staff_count = db.query(models.User).filter(models.User.store_id == store_id).count()
    if staff_count > 0:
        raise HTTPException(status_code=400, detail="该门店还绑定着店员账号，请先处理店员账号")

    db.query(models.Inventory).filter(models.Inventory.store_id == store_id).delete()
    db.delete(db_store)
    db.commit()
    return {"message": "删除成功"}


@router.get("/{store_id}/summary")
def store_summary(store_id: int, db: Session = Depends(get_db)):
    """门店今日销售概览（已撤销的订单不计入）"""
    store = db.query(models.Store).filter(models.Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    from datetime import date
    today = date.today()
    today_orders = db.query(models.Order).filter(
        models.Order.store_id == store_id,
        models.Order.status == "completed",
        func.date(models.Order.created_at) == today
    ).all()

    total_sales = sum(o.total_amount for o in today_orders)
    order_count = len(today_orders)

    low_stock = db.query(models.Inventory).filter(
        models.Inventory.store_id == store_id,
        models.Inventory.quantity <= 3,
        models.Inventory.quantity > 0
    ).count()

    out_of_stock = db.query(models.Inventory).filter(
        models.Inventory.store_id == store_id,
        models.Inventory.quantity == 0
    ).count()

    return {
        "store_name": store.name,
        "today_sales": total_sales,
        "today_orders": order_count,
        "low_stock_skus": low_stock,
        "out_of_stock_skus": out_of_stock,
    }
