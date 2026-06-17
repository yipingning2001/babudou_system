from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from database import get_db
from models import PurchaseOrder, PurchaseOrderItem, Inventory
from auth import get_current_user, check_store_access
import models

router = APIRouter(prefix="/purchases", tags=["进货管理"])


class PurchaseItemIn(BaseModel):
    product_id: int
    size: str
    quantity: int
    cost_price: float = 0


class PurchaseCreate(BaseModel):
    store_id: int
    supplier_id: Optional[int] = None
    note: Optional[str] = None
    items: List[PurchaseItemIn]


def _gen_order_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"PO{today}"
    count = db.query(PurchaseOrder).filter(PurchaseOrder.order_no.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:03d}"


def _load_full(db: Session, order_id: int) -> PurchaseOrder:
    return (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.store),
            joinedload(PurchaseOrder.supplier),
            joinedload(PurchaseOrder.operator),
            joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
        )
        .filter(PurchaseOrder.id == order_id)
        .first()
    )


def _fmt(o: PurchaseOrder) -> dict:
    total_qty = sum(i.quantity for i in o.items)
    total_amount = sum(i.quantity * i.cost_price for i in o.items)
    return {
        "id": o.id,
        "order_no": o.order_no,
        "store_id": o.store_id,
        "store_name": o.store.name if o.store else "",
        "supplier_id": o.supplier_id,
        "supplier_name": o.supplier.name if o.supplier else "散货",
        "operator_name": o.operator.display_name if o.operator else "",
        "status": o.status,
        "note": o.note or "",
        "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else "",
        "confirmed_at": o.confirmed_at.strftime("%Y-%m-%d %H:%M") if o.confirmed_at else None,
        "total_qty": total_qty,
        "total_amount": round(total_amount, 2),
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "product_name": (
                    f"{i.product.model_no} {i.product.name} {i.product.color}"
                    if i.product else ""
                ),
                "size": i.size,
                "quantity": i.quantity,
                "cost_price": i.cost_price,
                "subtotal": round(i.quantity * i.cost_price, 2),
            }
            for i in o.items
        ],
    }


@router.get("/")
def list_purchases(
    store_id: Optional[int] = None,
    date_str: Optional[str] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.store),
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.operator),
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
    )
    # 店员只能看自己门店的进货单
    if current_user.role == "staff":
        q = q.filter(PurchaseOrder.store_id == current_user.store_id)
    elif store_id:
        q = q.filter(PurchaseOrder.store_id == store_id)

    if supplier_id:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    if date_str:
        q = q.filter(func.date(PurchaseOrder.created_at) == date_str)

    orders = q.order_by(PurchaseOrder.created_at.desc()).all()
    return [_fmt(o) for o in orders]


@router.post("/")
def create_purchase(
    body: PurchaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not body.items:
        raise HTTPException(400, "至少填写一条进货明细")
    check_store_access(current_user, body.store_id)

    order = PurchaseOrder(
        order_no=_gen_order_no(db),
        store_id=body.store_id,
        supplier_id=body.supplier_id or None,
        operator_id=current_user.id,
        note=body.note,
        status="draft",
    )
    db.add(order)
    db.flush()

    for item in body.items:
        db.add(PurchaseOrderItem(
            order_id=order.id,
            product_id=item.product_id,
            size=item.size,
            quantity=item.quantity,
            cost_price=item.cost_price,
        ))

    db.commit()
    return _fmt(_load_full(db, order.id))


@router.get("/{id}")
def get_purchase(id: int, db: Session = Depends(get_db)):
    o = _load_full(db, id)
    if not o:
        raise HTTPException(404, "进货单不存在")
    return _fmt(o)


@router.post("/{id}/confirm")
def confirm_purchase(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    o = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.items))
        .filter(PurchaseOrder.id == id)
        .first()
    )
    if not o:
        raise HTTPException(404, "进货单不存在")
    if o.status == "confirmed":
        raise HTTPException(400, "该进货单已入库，不能重复操作")
    check_store_access(current_user, o.store_id)

    for item in o.items:
        inv = db.query(Inventory).filter(
            Inventory.store_id == o.store_id,
            Inventory.product_id == item.product_id,
            Inventory.size == item.size,
        ).first()
        if inv:
            inv.quantity += item.quantity
        else:
            db.add(Inventory(
                store_id=o.store_id,
                product_id=item.product_id,
                size=item.size,
                quantity=item.quantity,
            ))

    o.status = "confirmed"
    o.confirmed_at = datetime.now()
    db.commit()
    return {"ok": True, "message": "入库成功，库存已更新"}


@router.delete("/{id}")
def delete_purchase(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.id == id).first()
    if not o:
        raise HTTPException(404, "进货单不存在")
    if o.status == "confirmed":
        raise HTTPException(400, "已入库的进货单不能删除")
    check_store_access(current_user, o.store_id)
    db.delete(o)
    db.commit()
    return {"ok": True}
