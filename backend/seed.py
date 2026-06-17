"""
模拟数据生成脚本
运行方式：python seed.py
会生成：3家门店、10款商品、库存数据、20个模拟会员、50条历史订单
"""
import random
from datetime import datetime, timedelta
from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ── 清空旧数据（重新跑时用）──────────────────────────────────────────
db.query(models.OrderItem).delete()
db.query(models.Order).delete()
db.query(models.StockTransfer).delete()
db.query(models.Inventory).delete()
db.query(models.Member).delete()
db.query(models.Product).delete()
db.query(models.Store).delete()
db.commit()

# ── 1. 门店 ────────────────────────────────────────────────────────
# 地址、电话先留空，等你确认真实信息后再补（可以直接改这里重新跑seed.py，或者以后在管理页面里编辑）
stores_data = [
    {"name": "双丰巴布豆",       "address": "", "phone": ""},
    {"name": "广汇巴布豆",       "address": "", "phone": ""},
    {"name": "佳世客巴布豆一店", "address": "", "phone": ""},
    {"name": "佳世客巴布豆二店", "address": "", "phone": ""},
]
stores = []
for s in stores_data:
    store = models.Store(**s)
    db.add(store)
    stores.append(store)
db.flush()
print(f"[OK] 创建 {len(stores)} 家门店")

# ── 2. 商品（童鞋款式） ─────────────────────────────────────────────
products_data = [
    {"model_no": "BD2401", "name": "巴布豆春季运动鞋",   "color": "白色", "cost_price": 89,  "retail_price": 199},
    {"model_no": "BD2401", "name": "巴布豆春季运动鞋",   "color": "黑色", "cost_price": 89,  "retail_price": 199},
    {"model_no": "BD2402", "name": "巴布豆魔术贴学步鞋", "color": "粉色", "cost_price": 75,  "retail_price": 169},
    {"model_no": "BD2402", "name": "巴布豆魔术贴学步鞋", "color": "蓝色", "cost_price": 75,  "retail_price": 169},
    {"model_no": "BD2403", "name": "巴布豆秋季皮鞋",     "color": "棕色", "cost_price": 110, "retail_price": 249},
    {"model_no": "BD2403", "name": "巴布豆秋季皮鞋",     "color": "黑色", "cost_price": 110, "retail_price": 249},
    {"model_no": "BD2404", "name": "巴布豆冬季棉靴",     "color": "米白", "cost_price": 135, "retail_price": 299},
    {"model_no": "BD2404", "name": "巴布豆冬季棉靴",     "color": "灰色", "cost_price": 135, "retail_price": 299},
    {"model_no": "BD2405", "name": "巴布豆夏季凉鞋",     "color": "橙色", "cost_price": 55,  "retail_price": 129},
    {"model_no": "BD2405", "name": "巴布豆夏季凉鞋",     "color": "绿色", "cost_price": 55,  "retail_price": 129},
]
products = []
for p in products_data:
    product = models.Product(**p)
    db.add(product)
    products.append(product)
db.flush()
print(f"[OK] 创建 {len(products)} 款商品")

# ── 3. 库存（每家店 × 每款 × 每个鞋码） ────────────────────────────
sizes = ["22", "23", "24", "25", "26", "27", "28", "29", "30"]
for store in stores:
    for product in products:
        # 随机选取部分码数有货
        available_sizes = random.sample(sizes, random.randint(4, 8))
        for size in available_sizes:
            qty = random.randint(0, 12)
            db.add(models.Inventory(
                store_id=store.id,
                product_id=product.id,
                size=size,
                quantity=qty,
            ))
db.flush()
print("[OK] 生成库存数据")

# ── 4. 会员 ────────────────────────────────────────────────────────
child_names = ["小明", "小红", "豆豆", "乐乐", "涵涵", "壮壮", "甜甜", "旺旺", "妞妞", "宝宝",
               "皮皮", "可可", "欢欢", "点点", "丁丁", "糖糖", "多多", "朵朵", "阳阳", "佳佳"]
parent_surnames = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
                   "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗"]

members = []
for i in range(20):
    phone = f"138{random.randint(10000000, 99999999)}"
    birthday_years_ago = random.randint(2, 7)
    child_bday = datetime.now() - timedelta(days=birthday_years_ago * 365 + random.randint(0, 364))
    age_months = birthday_years_ago * 12
    if age_months <= 24:
        current_size = str(random.choice([22, 23, 24]))
    elif age_months <= 36:
        current_size = str(random.choice([24, 25, 26]))
    elif age_months <= 60:
        current_size = str(random.choice([26, 27, 28]))
    else:
        current_size = str(random.choice([28, 29, 30]))

    member = models.Member(
        phone=phone,
        name=f"{random.choice(parent_surnames)}女士",
        child_name=child_names[i],
        child_birthday=child_bday,
        current_size=current_size,
        register_store_id=random.choice(stores).id,
        total_spent=0,
        points=0,
    )
    db.add(member)
    members.append(member)
db.flush()
print(f"[OK] 创建 {len(members)} 个会员")

# ── 5. 历史订单（模拟过去60天的销售记录） ──────────────────────────
order_count = 0
for _ in range(50):
    store = random.choice(stores)
    member = random.choice(members) if random.random() > 0.3 else None
    days_ago = random.randint(0, 60)
    order_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 12))

    # 随机选1~3件商品
    num_items = random.randint(1, 2)
    selected_items = []
    total = 0

    for _ in range(num_items):
        product = random.choice(products)
        # 找一个有货的库存
        inv = db.query(models.Inventory).filter(
            models.Inventory.store_id == store.id,
            models.Inventory.product_id == product.id,
            models.Inventory.quantity >= 1,
        ).first()
        if not inv:
            continue
        qty = 1
        price = product.retail_price * random.choice([1.0, 0.95, 0.9])
        selected_items.append((product, inv, qty, round(price, 2)))
        total += qty * price

    if not selected_items:
        continue

    discount = round(total * random.choice([0, 0, 0, 0.05]), 2)
    order = models.Order(
        store_id=store.id,
        member_id=member.id if member else None,
        staff_name=random.choice(["小李", "小张", "小王"]),
        total_amount=round(total - discount, 2),
        discount_amount=discount,
        payment_method=random.choice(["微信", "微信", "支付宝", "现金"]),
        created_at=order_time,
    )
    db.add(order)
    db.flush()

    for product, inv, qty, price in selected_items:
        db.add(models.OrderItem(
            order_id=order.id,
            product_id=product.id,
            size=inv.size,
            quantity=qty,
            unit_price=price,
        ))
        inv.quantity -= qty

    if member:
        earned = int((total - discount) / 10)
        member.points += earned
        member.total_spent += round(total - discount, 2)

    order_count += 1

db.commit()
print(f"[OK] 生成 {order_count} 条历史订单")
print("\n数据库初始化完成！可以运行：uvicorn main:app --reload")
db.close()
