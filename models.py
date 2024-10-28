from database import Base 
from sqlalchemy import Column, Integer, String,DateTime,ForeignKey, func
from datetime import datetime
from sqlalchemy.orm import relationship

# User table
class Users(Base):
    __tablename__='users'
    id = Column(Integer, primary_key=True)
    first_name=Column(String, nullable=False)
    last_name=Column(String, nullable=False)
    email=Column(String, nullable=False, unique=True)
    phone=Column(String, nullable=False)
    password=Column(String, nullable=False)
    sales=relationship("Sales", back_populates='users')

# Products table
class Products(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    product_price = Column(Integer, nullable=False)
    selling_price = Column(Integer, nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, default=datetime.utcnow)
    sales=relationship("Sales", back_populates="products")

# Sales table
class Sales(Base):
    __tablename__='sales'
    id=Column(Integer, primary_key=True)
    pid = Column(Integer, ForeignKey('products.id'))
    user_id= Column(Integer, ForeignKey('users.id'))
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    products=relationship("Products", back_populates="sales")
    users=relationship("Users", back_populates='sales')
    






