from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)

    inventory = relationship("Inventory", back_populates="store")
    orders = relationship("Order", back_populates="store")
    members = relationship("Member", back_populates="register_store")
    transfers_out = relationship("StockTransfer", foreign_keys="StockTransfer.from_store_id", back_populates="from_store")
    transfers_in = relationship("StockTransfer", foreign_keys="StockTransfer.to_store_id", back_populates="to_store")


class Product(Base):
    """一个 Product = 一个款号 + 一个颜色，鞋码在 Inventory 里区分"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    model_no = Column(String(50), nullable=False)     # 款号，如 A103
    name = Column(String(200), nullable=False)         # 商品名称
    color = Column(String(50))                         # 颜色
    cost_price = Column(Float)                         # 进价
    retail_price = Column(Float)                       # 建议零售价
    image_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    inventory = relationship("Inventory", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    transfers = relationship("StockTransfer", back_populates="product")


class Inventory(Base):
    """每家门店 × 每个商品 × 每个鞋码 = 一条库存记录"""
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("store_id", "product_id", "size", name="uq_store_product_size"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size = Column(String(10), nullable=False)          # 鞋码，如 "26"、"27"
    quantity = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    store = relationship("Store", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    name = Column(String(50))                          # 家长姓名
    child_name = Column(String(50))                    # 孩子姓名
    child_birthday = Column(DateTime)                  # 孩子生日（用于生日营销）
    current_size = Column(String(10))                  # 孩子当前穿的鞋码
    points = Column(Integer, default=0)               # 积分
    total_spent = Column(Float, default=0)            # 累计消费金额
    register_store_id = Column(Integer, ForeignKey("stores.id"))
    created_at = Column(DateTime, default=datetime.now)

    register_store = relationship("Store", back_populates="members")
    orders = relationship("Order", back_populates="member")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True)   # 可以是非会员购买
    staff_name = Column(String(50))
    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0)
    payment_method = Column(String(20), default="微信")   # 微信/支付宝/现金/银行卡
    status = Column(String(20), default="completed")       # completed / voided（已撤销/退货）
    voided_at = Column(DateTime, nullable=True)
    voided_reason = Column(String(200), nullable=True)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    store = relationship("Store", back_populates="orders")
    member = relationship("Member", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)          # 实际成交价

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class User(Base):
    """登录账号。role=owner 是老板，能看所有门店；role=staff 是店员，绑定单一门店"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(100), nullable=False)
    display_name = Column(String(50))
    role = Column(String(20), nullable=False, default="staff")   # owner / staff
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)  # owner 为 null，可看所有店
    created_at = Column(DateTime, default=datetime.now)

    store = relationship("Store")


class ProductBarcode(Base):
    """
    厂家印在鞋盒/吊牌上的条形码 与 商品+鞋码 的绑定关系。
    一个条码只对应一个款式+颜色+鞋码（同一双鞋不同尺码条码不同）。
    跟门店无关——不管哪家店收到这双鞋，条码都是同一个。
    """
    __tablename__ = "product_barcodes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size = Column(String(10), nullable=False)
    barcode = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)

    product = relationship("Product")


class StockTransfer(Base):
    """门店间调货记录"""
    __tablename__ = "stock_transfers"

    id = Column(Integer, primary_key=True, index=True)
    from_store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    to_store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    from_store = relationship("Store", foreign_keys=[from_store_id], back_populates="transfers_out")
    to_store = relationship("Store", foreign_keys=[to_store_id], back_populates="transfers_in")
    product = relationship("Product", back_populates="transfers")


# ── 进货管理（进销存的"进"）────────────────────────────


class Supplier(Base):
    """供应商档案"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    contact_name = Column(String(50))
    phone = Column(String(20))
    address = Column(String(200))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(Base):
    """进货单：记录每次从供应商收货的单据"""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(30), unique=True, nullable=False)   # 如 PO20260617001
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="draft")   # draft=草稿 / confirmed=已入库
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    confirmed_at = Column(DateTime, nullable=True)

    store = relationship("Store")
    supplier = relationship("Supplier", back_populates="purchase_orders")
    operator = relationship("User")
    items = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    """进货单明细：每行一个商品+鞋码"""
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    cost_price = Column(Float, nullable=False, default=0)

    order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")
