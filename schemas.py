from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional



# Pydantic model for user creation
class User(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    password: str
    confirm_password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

# User schema for response (output)
class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# class LoginRequest(BaseModel):
#     email: str
#     password: str

# class LoginResponse(BaseModel):
#     message: str
#     user_id: int


# Schema for creating a new product
class Product(BaseModel):
    product_name: str
    product_price: int
    selling_price: int
    stock_quantity: int


# Schema for returning a sale (with additional fields)
class Sale(BaseModel):
    pid: int  # Product ID
    user_id: int  # User ID (customer)
    quantity: int  # Quantity of the product sold
    # sale_date: datetime  # Date of the sale




