from pydantic import BaseModel, EmailStr, validator, Field
from datetime import date
from typing import Optional, List, Dict, Any
from datetime import datetime
import re




# Pydantic model for user creation
class UserBase(BaseModel):
    """المخطط الأساسي للمستخدم"""
    email: EmailStr
    first_name: str
    last_name: str
    phone: str

    @validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

class UserCreate(UserBase):
    """مخطط إنشاء مستخدم جديد"""
    password: str = Field(..., min_length=6)
    confirm_password: str

    @validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserUpdate(BaseModel):
    """مخطط تحديث المستخدم"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None

    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @validator('password')
    def validate_password(cls, v):
        if v and len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class UserLogin(BaseModel):
    """مخطط تسجيل الدخول"""
    email: EmailStr
    password: str

class UserResponse(UserBase):
    """مخطط استجابة بيانات المستخدم"""
    id: int
    created_at: datetime  
    updated_at: datetime | None = None     #

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TokenResponse(BaseModel):
    """مخطط استجابة التوكن الكامل"""
    access_token: str
    access_token_expires: datetime
    refresh_token: str
    refresh_token_expires: datetime
    token_type: str = "bearer"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TokenData(BaseModel):
    """مخطط بيانات التوكن المستخرجة"""
    email: Optional[str] = None
    token_type: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    """مخطط طلب تجديد التوكن"""
    refresh_token: str


# class LoginRequest(BaseModel):
#     email: str
#     password: str

# class LoginResponse(BaseModel):
#     message: str
#     user_id: int


# Schema for creating a new product

# Base Product Schema (shared properties)
class ProductBase(BaseModel):
    product_name: str
    description: Optional[str] = None
    product_price: int
    selling_price: int
    stock_quantity: int
    image_url: Optional[str] = None

# Schema for creating a product
class ProductCreate(ProductBase):
    pass

# Schema for reading a product (includes ID and timestamps)
class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        # orm_mode = True   # This will cause a warning in Pydantic V2
        from_attributes = True  # Updated for Pydantic V2

# Schema for updating a product
class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    product_price: Optional[int] = None
    selling_price: Optional[int] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None

# Schema for product response
class ProductResponse(ProductCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    vendor: Optional['VendorBase'] = None  # Add vendor relationship

    class Config:
        from_attributes = True


# Vendor Schema:
class VendorBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorUpdate(VendorBase):
    pass

class Vendor(VendorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True




# Schema for returning a sale 
class Sale(BaseModel):
    pid: int
    quantity: int
    user_id: int  

# This schema for user profile:
class SaleBase(BaseModel):
    product_name: str
    quantity: int
    total_amount: float
    created_at: datetime

class UpdateSale(BaseModel):
    pid: int
    user_id: int
    quantity: int
    price: float
    date: date

    class Config:
        # orm_mode = True   # This will cause a warning in Pydantic V2
        from_attributes = True  # Updated for Pydantic V2

# This schema for user profile:
class Statistics(BaseModel):
    total_sales: int
    total_products: int
    revenue: float

class ContactBase(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

class ContactCreate(ContactBase):
    pass

class ContactResponse(ContactBase):
    id: int
    created_at: datetime
    status: str  # e.g., 'pending', 'responded', 'closed'
    response: Optional[str] = None

    class Config:
        from_attributes = True


class ReplyCreate(BaseModel):
    reply: str

    class Config:
        from_attributes = True




class ImportHistoryBase(BaseModel):
    filename: str
    status: str
    total_rows: Optional[int]
    successful_rows: Optional[int]
    failed_rows: Optional[int]
    errors: Optional[List[Dict[str, Any]]]
    created_at: datetime
    completed_at: Optional[datetime]
    user_id: Optional[int]

    class Config:
        orm_mode = True

class ImportHistoryCreate(BaseModel):
    filename: str
    user_id: Optional[int]

class ImportHistoryResponse(ImportHistoryBase):
    id: int




class UserActivity(BaseModel):
    recent_sales: List[SaleBase]
    recent_products: List[ProductBase]
    statistics: Statistics






# # Schema for Category:
# class CategoryBase(BaseModel):
#     name: str
#     description: Optional[str] = None
#     icon: Optional[str] = None

# class CategoryCreate(CategoryBase):
#     pass

# class Category(CategoryBase):
#     id: int
#     product_count: Optional[int] = 0
#     popular_products: Optional[List[dict]] = []

#     class Config:
#         # orm_mode = True   # This will cause a warning in Pydantic V2
#         from_attributes = True  # Updated for Pydantic V2




class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        if not re.search(r"[A-Za-z]", v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r"[0-9]", v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError('Password must contain at least one special character')
        return v



