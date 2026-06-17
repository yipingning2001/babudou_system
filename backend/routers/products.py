from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
from auth import require_owner

router = APIRouter(prefix="/products", tags=["商品"])


class ProductCreate(BaseModel):
    model_no: str
    name: str
    color: Optional[str] = None
    cost_price: Optional[float] = None
    retail_price: Optional[float] = None
    image_url: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    model_no: str
    name: str
    color: Optional[str]
    cost_price: Optional[float]
    retail_price: Optional[float]
    image_url: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("/", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db), _owner: models.User = Depends(require_owner)):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db), _owner: models.User = Depends(require_owner)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    for key, value in product.model_dump().items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _owner: models.User = Depends(require_owner)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")

    sold_count = db.query(models.OrderItem).filter(models.OrderItem.product_id == product_id).count()
    if sold_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该商品已有 {sold_count} 笔销售记录，不能删除（会破坏历史订单数据）。如果不再卖了，可以把库存清零即可。",
        )

    db.query(models.Inventory).filter(models.Inventory.product_id == product_id).delete()
    db.delete(db_product)
    db.commit()
    return {"message": "删除成功"}
