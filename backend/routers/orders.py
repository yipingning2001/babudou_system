from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from database import get_db
import models
from auth import get_current_user, check_store_access

router = APIRouter(prefix="/orders", tags=["订单"])

POINTS_RATE = 10  # 每消费10元得1积分


class OrderItemIn(BaseModel):
    product_id: int
    size: str
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    store_id: int
    member_phone: Optional[str] = None    # 通过手机号找会员，为空则非会员购买
    items: list[OrderItemIn]
    discount_amount: float = 0
    payment_method: str = "微信"
    note: Optional[str] = None


class VoidOrderIn(BaseModel):
    reason: Optional[str] = None


@router.post("/")
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    开单：一次完成
    1. 检查库存
    2. 扣减库存
    3. 写订单和明细
    4. 更新会员消费和积分
    """
    check_store_access(current_user, order.store_id)

    store = db.query(models.Store).filter(models.Store.id == order.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    # 查找会员（可选）
    member = None
    if order.member_phone:
        member = db.query(models.Member).filter(models.Member.phone == order.member_phone).first()
        if not member:
            raise HTTPException(status_code=404, detail=f"手机号 {order.member_phone} 未找到会员，请先注册")

    # 检查所有商品库存是否充足（先全部检查，再统一扣减，避免部分扣减后报错）
    inventory_rows = []
    for item in order.items:
        inv = db.query(models.Inventory).filter(
            models.Inventory.store_id == order.store_id,
            models.Inventory.product_id == item.product_id,
            models.Inventory.size == item.size,
        ).first()
        if not inv or inv.quantity < item.quantity:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            name = product.name if product else f"商品ID {item.product_id}"
            current_qty = inv.quantity if inv else 0
            raise HTTPException(
                status_code=400,
                detail=f"{name} {item.size}码 库存不足（当前{current_qty}双，需要{item.quantity}双）"
            )
        inventory_rows.append((inv, item.quantity))

    # 计算总金额
    total = sum(i.unit_price * i.quantity for i in order.items) - order.discount_amount

    # 创建订单
    db_order = models.Order(
        store_id=order.store_id,
        member_id=member.id if member else None,
        staff_name=current_user.display_name or current_user.username,
        total_amount=total,
        discount_amount=order.discount_amount,
        payment_method=order.payment_method,
        status="completed",
        note=order.note,
    )
    db.add(db_order)
    db.flush()  # 获取 order.id，但不提交

    # 写订单明细 + 扣库存
    for item in order.items:
        db.add(models.OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            size=item.size,
            quantity=item.quantity,
            unit_price=item.unit_price,
        ))
    for inv, qty in inventory_rows:
        inv.quantity -= qty

    # 更新会员积分和消费额
    if member:
        earned_points = int(total / POINTS_RATE)
        member.points += earned_points
        member.total_spent += total

    db.commit()
    db.refresh(db_order)

    return {
        "order_id": db_order.id,
        "total_amount": total,
        "earned_points": int(total / POINTS_RATE) if member else 0,
        "message": "开单成功",
    }


@router.get("/")
def list_orders(
    store_id: Optional[int] = None,
    date_str: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """查询订单列表，支持按门店和日期筛选"""
    from sqlalchemy import func
    query = db.query(models.Order)
    if current_user.role == "staff":
        query = query.filter(models.Order.store_id == current_user.store_id)
    elif store_id:
        query = query.filter(models.Order.store_id == store_id)
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
            query = query.filter(func.date(models.Order.created_at) == target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请用 YYYY-MM-DD")
    orders = query.order_by(models.Order.created_at.desc()).limit(100).all()
    return [
        {
            "order_id": o.id,
            "store_id": o.store_id,
            "member_id": o.member_id,
            "total_amount": o.total_amount,
            "payment_method": o.payment_method,
            "status": o.status,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M"),
            "items_count": len(o.items),
        }
        for o in orders
    ]


@router.get("/{order_id}/receipt")
def get_receipt(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """开单成功后拉取小票内容用于打印"""
    o = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="订单不存在")
    check_store_access(current_user, o.store_id)
    return {
        "order_id": o.id,
        "store_name": o.store.name,
        "staff_name": o.staff_name,
        "member_phone": o.member.phone if o.member else None,
        "member_points": o.member.points if o.member else None,
        "payment_method": o.payment_method,
        "discount_amount": o.discount_amount,
        "total_amount": o.total_amount,
        "status": o.status,
        "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "items": [
            {
                "name": f"{item.product.model_no} {item.product.name} {item.product.color}",
                "size": item.size,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": round(item.unit_price * item.quantity, 2),
            }
            for item in o.items
        ],
    }


@router.post("/{order_id}/void")
def void_order(
    order_id: int,
    body: VoidOrderIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    撤销/退货：
    1. 恢复库存
    2. 回退会员积分和累计消费
    3. 标记订单为已撤销（保留记录，不物理删除）
    """
    o = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="订单不存在")
    check_store_access(current_user, o.store_id)
    if o.status == "voided":
        raise HTTPException(status_code=400, detail="该订单已经是撤销状态")

    # 恢复库存
    for item in o.items:
        inv = db.query(models.Inventory).filter(
            models.Inventory.store_id == o.store_id,
            models.Inventory.product_id == item.product_id,
            models.Inventory.size == item.size,
        ).first()
        if inv:
            inv.quantity += item.quantity
        else:
            db.add(models.Inventory(
                store_id=o.store_id,
                product_id=item.product_id,
                size=item.size,
                quantity=item.quantity,
            ))

    # 回退会员积分和消费额
    if o.member_id:
        member = db.query(models.Member).filter(models.Member.id == o.member_id).first()
        if member:
            earned_points = int(o.total_amount / POINTS_RATE)
            member.points = max(0, member.points - earned_points)
            member.total_spent = max(0, member.total_spent - o.total_amount)

    o.status = "voided"
    o.voided_at = datetime.now()
    o.voided_reason = body.reason
    db.commit()

    return {"message": "撤销成功，库存已恢复"}


@router.get("/report/all-stores")
def sales_report_all_stores(
    date_str: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    单日全门店销售汇总：每家店的销售额 + 总计。
    店员只能看到自己门店那一条（前端一般不会给店员展示这个视图，后端也兜底限制一下）。
    """
    from sqlalchemy import func
    target_date = date.fromisoformat(date_str) if date_str else date.today()

    stores = db.query(models.Store).order_by(models.Store.id).all()
    if current_user.role == "staff":
        stores = [s for s in stores if s.id == current_user.store_id]

    store_rows = []
    grand_total_sales = 0.0
    grand_total_orders = 0

    for store in stores:
        orders = db.query(models.Order).filter(
            models.Order.store_id == store.id,
            func.date(models.Order.created_at) == target_date,
            models.Order.status == "completed",
        ).all()
        store_sales = sum(o.total_amount for o in orders)
        store_rows.append({
            "store_id": store.id,
            "store_name": store.name,
            "total_orders": len(orders),
            "total_sales": round(store_sales, 2),
        })
        grand_total_sales += store_sales
        grand_total_orders += len(orders)

    return {
        "date": str(target_date),
        "stores": store_rows,
        "grand_total_sales": round(grand_total_sales, 2),
        "grand_total_orders": grand_total_orders,
    }


@router.get("/report")
def sales_report(
    store_id: Optional[int] = None,
    date_str: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """日销售汇总报表（已撤销的订单不计入统计）"""
    from sqlalchemy import func
    target_date = date.fromisoformat(date_str) if date_str else date.today()

    query = db.query(models.Order).filter(
        func.date(models.Order.created_at) == target_date,
        models.Order.status == "completed",
    )
    if current_user.role == "staff":
        query = query.filter(models.Order.store_id == current_user.store_id)
    elif store_id:
        query = query.filter(models.Order.store_id == store_id)

    orders = query.all()
    total_sales = sum(o.total_amount for o in orders)
    total_discount = sum(o.discount_amount for o in orders)
    member_orders = sum(1 for o in orders if o.member_id)

    payment_breakdown: dict = {}
    for o in orders:
        payment_breakdown[o.payment_method] = payment_breakdown.get(o.payment_method, 0) + o.total_amount

    return {
        "date": str(target_date),
        "total_orders": len(orders),
        "total_sales": round(total_sales, 2),
        "total_discount": round(total_discount, 2),
        "member_orders": member_orders,
        "non_member_orders": len(orders) - member_orders,
        "payment_breakdown": payment_breakdown,
    }
