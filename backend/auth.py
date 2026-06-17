"""
登录鉴权：密码加密（bcrypt）+ JWT token。
角色说明：
  owner（老板）—— store_id 为空，能看/管所有门店
  staff（店员）—— 绑定单一门店，只能操作自己门店的数据
"""
import os
from datetime import datetime, timedelta

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
import models

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "babadou_secret_key_change_this_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())


def create_access_token(user: "models.User") -> str:
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "store_id": user.store_id,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> "models.User":
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录已失效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_error

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise credentials_error
    return user


def require_owner(current_user: "models.User" = Depends(get_current_user)) -> "models.User":
    if current_user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有老板账号才能执行此操作")
    return current_user


def check_store_access(current_user: "models.User", store_id: int):
    """店员只能操作自己门店的数据，老板不限制"""
    if current_user.role == "staff" and current_user.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作其他门店的数据")
