from app.database import Base 
from sqlalchemy import Column, Integer, String,DateTime,ForeignKey,Text,func,JSON,Boolean
from datetime import datetime
from sqlalchemy.orm import relationship


# User table:
class Users(Base):
    __tablename__='users'
    id = Column(Integer, primary_key=True)
    first_name=Column(String, nullable=False)
    last_name=Column(String, nullable=False)
    email=Column(String, nullable=False, unique=True)
    phone=Column(String, nullable=False)
    password=Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())  # Automatically set to the current time
    updated_at = Column(DateTime, onupdate=func.now())
    sales=relationship("Sales", back_populates='users')
    reset_tokens = relationship("PasswordResetTokens", back_populates="user", cascade="all, delete-orphan")
    
    # products = relationship("Products", back_populates="owner")



# ... existing imports and models ...

class PasswordResetTokens(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    user = relationship("Users", back_populates="reset_tokens")


# Products table:
class Products(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    product_price = Column(Integer, nullable=False)
    selling_price = Column(Integer, nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    description = Column(Text, nullable=True) 
    image_url = Column(String(255), nullable=True) 
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vendor = relationship("Vendor", back_populates="products")
    sales = relationship("Sales", back_populates="products")



class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_person = Column(String)
    email = Column(String, unique=True)
    phone = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with products (one vendor can have many products)
    products = relationship("Products", back_populates="vendor")



# Sales table:
class Sales(Base):
    __tablename__='sales'
    id=Column(Integer, primary_key=True)
    pid = Column(Integer, ForeignKey('products.id'))
    user_id= Column(Integer, ForeignKey('users.id'))
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    products=relationship("Products", back_populates="sales")
    users=relationship("Users", back_populates='sales')


# Contact table:
class Contact(Base):
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default='unread')  # pending, responded, closed
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# ImportHistory table:
class ImportHistory(Base):
    __tablename__ = 'import_history'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    status = Column(String)  # 'completed', 'failed', 'processing'
    total_rows = Column(Integer)
    successful_rows = Column(Integer)
    failed_rows = Column(Integer)
    errors = Column(JSON)  # Store error details as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'))



    
# Category table
# class Category(Base):
#     __tablename__ = "categories"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), unique=True, index=True)
#     description = Column(Text)
#     icon = Column(String(255))  # رابط الأيقونة
#     products = relationship("Products", back_populates="category")


# class Category(Base):
#     __tablename__ = 'categories'

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String, unique=True, index=True, nullable=False)
#     description = Column(String, nullable=True)
#     created_at =  Column(DateTime, onupdate=datetime.utcnow, default=datetime.utcnow)
#     updated_at =  Column(DateTime, onupdate=datetime.utcnow, default=datetime.utcnow)




