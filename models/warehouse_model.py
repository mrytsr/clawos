"""
仓库管理系统 - 数据库模型
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Warehouse(SQLModel, table=True):
    """仓库"""
    __tablename__ = "warehouses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    location: str = ""
    description: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class Product(SQLModel, table=True):
    """商品 - 归属仓库"""
    __tablename__ = "products"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(index=True, foreign_key="warehouses.id")
    name: str = Field(index=True)
    unit_price: float = 0.0
    unit: str = "斤"
    current_stock: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class Transaction(SQLModel, table=True):
    """出入库记录"""
    __tablename__ = "transactions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(index=True, foreign_key="products.id")
    type: str = Field(index=True)  # 入库 / 出库
    quantity: float
    stock_after: float
    date: str = Field(index=True)
    note: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
