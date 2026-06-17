"""
创建登录账号：4个老板账号（看所有门店）+ 15个店员账号（按4家店分配）。
可重复运行，已存在的用户名不会被覆盖（不会重置密码）。
运行方式：python seed_users.py
"""
from database import SessionLocal, engine
import models
from auth import hash_password

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

DEFAULT_PASSWORD = "888888"  # 统一默认密码，建议上线前提醒大家自己改


def create_if_missing(username, password, display_name, role, store_id=None):
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        print(f"[SKIP] {username} 已存在，未改动")
        return
    user = models.User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        store_id=store_id,
    )
    db.add(user)
    print(f"[OK] 创建 {role} 账号：{username} / {password} （{display_name}）")


# ── 4个老板账号（不绑定门店，能看所有门店数据）──────────────────
for i in range(1, 5):
    create_if_missing(
        username=f"boss{i}",
        password=DEFAULT_PASSWORD,
        display_name=f"老板{i}",
        role="owner",
    )

db.commit()

# ── 15个店员账号，按4家店分配（4/4/4/3）──────────────────────
stores = db.query(models.Store).order_by(models.Store.id).all()
if len(stores) != 4:
    print(f"[警告] 当前门店数量是 {len(stores)}，不是4家，分配可能不准确，请先确认 seed.py 已正确生成4家门店")

staff_per_store = [4, 4, 4, 3]
staff_index = 1
for store, count in zip(stores, staff_per_store):
    for n in range(1, count + 1):
        username = f"staff{staff_index:02d}"
        create_if_missing(
            username=username,
            password=DEFAULT_PASSWORD,
            display_name=f"{store.name}-店员{n}",
            role="staff",
            store_id=store.id,
        )
        staff_index += 1

db.commit()
print("\n账号创建完成。所有账号默认密码统一是：888888")
db.close()
