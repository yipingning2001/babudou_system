from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
from auth import get_current_user, check_store_access

router = APIRouter(prefix="/inventory", tags=["库存"])


class InventoryUpsert(BaseModel):
    store_id: int
    product_id: int
    size: str
    quantity: int


class TransferCreate(BaseModel):
    from_store_id: int
    to_store_id: int
    product_id: int
    size: str
    quantity: int
    note: Optional[str] = None


@router.get("/store/{store_id}")
def get_store_inventory(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """查询某家门店的全部库存，按商品分组"""
    check_store_access(current_user, store_id)
    rows = (
        db.query(models.Inventory)
        .options(joinedload(models.Inventory.product))
        .filter(models.Inventory.store_id == store_id)
        .order_by(models.Inventory.product_id, models.Inventory.size)
        .all()
    )

    grouped: dict = {}
    for row in rows:
        p = row.product
        key = p.id
        if key not in grouped:
            grouped[key] = {
                "product_id": p.id,
                "model_no": p.model_no,
                "name": p.name,
                "color": p.color,
                "retail_price": p.retail_price,
                "sizes": [],
            }
        grouped[key]["sizes"].append({"size": row.size, "quantity": row.quantity})

    return list(grouped.values())


@router.post("/upsert")
def upsert_inventory(
    data: InventoryUpsert,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """新建或更新库存（入库用）"""
    check_store_access(current_user, data.store_id)
    row = db.query(models.Inventory).filter(
        models.Inventory.store_id == data.store_id,
        models.Inventory.product_id == data.product_id,
        models.Inventory.size == data.size,
    ).first()

    if row:
        row.quantity += data.quantity
    else:
        row = models.Inventory(**data.model_dump())
        db.add(row)

    db.commit()
    db.refresh(row)
    return {"store_id": row.store_id, "product_id": row.product_id, "size": row.size, "quantity": row.quantity}


@router.post("/transfer")
def transfer_stock(
    data: TransferCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """门店间调货：A店库存减，B店库存加"""
    check_store_access(current_user, data.from_store_id)
    if data.from_store_id == data.to_store_id:
        raise HTTPException(status_code=400, detail="调出和调入门店不能相同")

    source = db.query(models.Inventory).filter(
        models.Inventory.store_id == data.from_store_id,
        models.Inventory.product_id == data.product_id,
        models.Inventory.size == data.size,
    ).first()

    if not source or source.quantity < data.quantity:
        raise HTTPException(status_code=400, detail="调出门店库存不足")

    source.quantity -= data.quantity

    dest = db.query(models.Inventory).filter(
        models.Inventory.store_id == data.to_store_id,
        models.Inventory.product_id == data.product_id,
        models.Inventory.size == data.size,
    ).first()

    if dest:
        dest.quantity += data.quantity
    else:
        dest = models.Inventory(
            store_id=data.to_store_id,
            product_id=data.product_id,
            size=data.size,
            quantity=data.quantity,
        )
        db.add(dest)

    transfer_record = models.StockTransfer(
        from_store_id=data.from_store_id,
        to_store_id=data.to_store_id,
        product_id=data.product_id,
        size=data.size,
        quantity=data.quantity,
        note=data.note,
    )
    db.add(transfer_record)
    db.commit()
    return {"message": "调货成功", "transfer_id": transfer_record.id}


@router.get("/low-stock")
def low_stock_alert(
    threshold: int = 3,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """查询库存告急的SKU（数量 <= threshold）。店员只看自己门店，老板看全部"""
    query = (
        db.query(models.Inventory)
        .options(joinedload(models.Inventory.product), joinedload(models.Inventory.store))
        .filter(models.Inventory.quantity <= threshold)
    )
    if current_user.role == "staff":
        query = query.filter(models.Inventory.store_id == current_user.store_id)
    rows = query.order_by(models.Inventory.quantity).all()
    return [
        {
            "store": row.store.name,
            "product": f"{row.product.model_no} {row.product.name} {row.product.color}",
            "size": row.size,
            "quantity": row.quantity,
        }
        for row in rows
    ]
