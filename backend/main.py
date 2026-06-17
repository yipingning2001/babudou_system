from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from auth import get_current_user
from routers import stores, products, inventory, members, orders, barcodes, auth as auth_router, suppliers, purchases, analytics

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="巴布豆门店管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# /auth 不需要登录（登录本身），其余所有接口都要求带 token
app.include_router(auth_router.router)
app.include_router(stores.router, dependencies=[Depends(get_current_user)])
app.include_router(products.router, dependencies=[Depends(get_current_user)])
app.include_router(inventory.router, dependencies=[Depends(get_current_user)])
app.include_router(members.router, dependencies=[Depends(get_current_user)])
app.include_router(orders.router, dependencies=[Depends(get_current_user)])
app.include_router(barcodes.router, dependencies=[Depends(get_current_user)])
app.include_router(suppliers.router, dependencies=[Depends(get_current_user)])
app.include_router(purchases.router, dependencies=[Depends(get_current_user)])
app.include_router(analytics.router, dependencies=[Depends(get_current_user)])


@app.get("/")
def root():
    return {"message": "巴布豆门店管理系统 API 正常运行"}
