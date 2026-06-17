from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta
from database import get_db
import models
from auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["数据分析"])


def _date_range(period: str):
    today = date.today()
    if period == "today":
        return today, today
    elif period == "week":
        return today - timedelta(days=6), today
    elif period == "month":
        return today.replace(day=1), today
    return None, None  # all


def _order_query(db, current_user, store_id, start_date, end_date):
    q = db.query(models.Order).filter(models.Order.status == "completed")
    if current_user.role == "staff":
        q = q.filter(models.Order.store_id == current_user.store_id)
    elif store_id:
        q = q.filter(models.Order.store_id == store_id)
    if start_date:
        q = q.filter(func.date(models.Order.created_at) >= start_date)
    if end_date:
        q = q.filter(func.date(models.Order.created_at) <= end_date)
    return q


@router.get("/profit")
def get_profit(
    period: str = "month",
    store_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """利润总览：实现利润 + 在库利润 + 草稿进货单数"""
    start_date, end_date = _date_range(period)

    orders = _order_query(db, current_user, store_id, start_date, end_date).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product)
    ).all()

    total_sales = round(sum(o.total_amount for o in orders), 2)
    total_orders = len(orders)

    realized_profit = 0.0
    for o in orders:
        for item in o.items:
            cost = (item.product.cost_price or 0) if item.product else 0
            realized_profit += (item.unit_price - cost) * item.quantity

    # 在库利润（库存里的潜在利润，不受时间筛选影响）
    inv_q = db.query(models.Inventory).options(
        joinedload(models.Inventory.product)
    ).filter(models.Inventory.quantity > 0)
    if current_user.role == "staff":
        inv_q = inv_q.filter(models.Inventory.store_id == current_user.store_id)
    elif store_id:
        inv_q = inv_q.filter(models.Inventory.store_id == store_id)

    inv_rows = inv_q.all()
    inventory_profit = sum(
        ((r.product.retail_price or 0) - (r.product.cost_price or 0)) * r.quantity
        for r in inv_rows if r.product
    )
    inventory_value = sum(
        (r.product.cost_price or 0) * r.quantity
        for r in inv_rows if r.product
    )

    # 待确认进货单数量
    draft_q = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.status == "draft")
    if current_user.role == "staff":
        draft_q = draft_q.filter(models.PurchaseOrder.store_id == current_user.store_id)
    elif store_id:
        draft_q = draft_q.filter(models.PurchaseOrder.store_id == store_id)

    return {
        "period": period,
        "total_sales": total_sales,
        "total_orders": total_orders,
        "realized_profit": round(realized_profit, 2),
        "inventory_profit": round(inventory_profit, 2),
        "total_profit": round(realized_profit + inventory_profit, 2),
        "inventory_value": round(inventory_value, 2),
        "draft_purchases": draft_q.count(),
    }


@router.get("/top-products")
def get_top_products(
    period: str = "month",
    store_id: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """畅销/滞销商品排行"""
    start_date, end_date = _date_range(period)

    orders = _order_query(db, current_user, store_id, start_date, end_date).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product)
    ).all()

    # 按商品汇总销售
    stats: dict = {}
    for o in orders:
        for item in o.items:
            pid = item.product_id
            if pid not in stats:
                stats[pid] = {
                    "product_id": pid,
                    "name": (
                        f"{item.product.model_no} {item.product.name} {item.product.color}"
                        if item.product else f"商品{pid}"
                    ),
                    "qty_sold": 0,
                    "revenue": 0.0,
                }
            stats[pid]["qty_sold"] += item.quantity
            stats[pid]["revenue"] += item.unit_price * item.quantity

    sorted_list = sorted(stats.values(), key=lambda x: x["qty_sold"], reverse=True)
    top_sellers = [
        {**p, "revenue": round(p["revenue"], 2)}
        for p in sorted_list[:limit]
    ]

    # 滞销：库存多但本期卖得少的
    inv_q = db.query(models.Inventory).options(
        joinedload(models.Inventory.product)
    ).filter(models.Inventory.quantity > 0)
    if current_user.role == "staff":
        inv_q = inv_q.filter(models.Inventory.store_id == current_user.store_id)
    elif store_id:
        inv_q = inv_q.filter(models.Inventory.store_id == store_id)

    inv_rows = inv_q.order_by(models.Inventory.quantity.desc()).all()

    # 按商品合并库存
    inv_by_product: dict = {}
    for r in inv_rows:
        pid = r.product_id
        if pid not in inv_by_product:
            inv_by_product[pid] = {
                "product_id": pid,
                "name": (
                    f"{r.product.model_no} {r.product.name} {r.product.color}"
                    if r.product else f"商品{pid}"
                ),
                "qty_in_stock": 0,
            }
        inv_by_product[pid]["qty_in_stock"] += r.quantity

    slow_movers = []
    for pid, info in sorted(inv_by_product.items(), key=lambda x: x[1]["qty_in_stock"], reverse=True):
        qty_sold = stats.get(pid, {}).get("qty_sold", 0)
        if qty_sold < 3:
            slow_movers.append({**info, "qty_sold": qty_sold})
        if len(slow_movers) >= limit:
            break

    return {
        "period": period,
        "top_sellers": top_sellers,
        "slow_movers": slow_movers,
    }
