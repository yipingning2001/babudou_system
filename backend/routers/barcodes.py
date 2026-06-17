from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models

router = APIRouter(prefix="/barcodes", tags=["条码"])


class BarcodeBind(BaseModel):
    barcode: str
    product_id: int
    size: str


@router.post("/bind")
def bind_barcode(data: BarcodeBind, db: Session = Depends(get_db)):
    """
    把厂家印的条码绑定到某个商品+鞋码。
    入库扫码时用：第一次扫到没绑定过的码，选好商品+鞋码后调用这个接口绑定。
    同一个码已经绑过的话，这次会改成新的绑定（用于纠错）。
    """
    product = db.query(models.Product).filter(models.Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    existing = db.query(models.ProductBarcode).filter(models.ProductBarcode.barcode == data.barcode).first()
    if existing:
        existing.product_id = data.product_id
        existing.size = data.size
    else:
        existing = models.ProductBarcode(barcode=data.barcode, product_id=data.product_id, size=data.size)
        db.add(existing)

    db.commit()
    return {"message": "绑定成功", "barcode": data.barcode, "product_id": data.product_id, "size": data.size}


@router.get("/lookup")
def lookup_barcode(barcode: str, store_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    扫码查询：给一个条码，返回它对应的商品+鞋码信息。
    传 store_id 的话，还会一起返回该门店这个码当前的库存数量（收银台用）。
    """
    binding = db.query(models.ProductBarcode).filter(models.ProductBarcode.barcode == barcode).first()
    if not binding:
        raise HTTPException(status_code=404, detail="这个条码还没有绑定过商品，请先在「库存管理」入库时扫码绑定")

    product = db.query(models.Product).filter(models.Product.id == binding.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="绑定的商品已被删除，请重新绑定")

    result = {
        "barcode": barcode,
        "product_id": product.id,
        "model_no": product.model_no,
        "name": product.name,
        "color": product.color,
        "retail_price": product.retail_price,
        "size": binding.size,
        "stock_quantity": None,
    }

    if store_id:
        inv = db.query(models.Inventory).filter(
            models.Inventory.store_id == store_id,
            models.Inventory.product_id == product.id,
            models.Inventory.size == binding.size,
        ).first()
        result["stock_quantity"] = inv.quantity if inv else 0

    return result
