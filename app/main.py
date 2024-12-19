import re # Pattern Matching: Regular expressions allow you to define a search pattern. This pattern can be used to check if a string contains specific characters, words, or sequences.
import os
from pathlib import Path 
import io
from fastapi.staticfiles import StaticFiles
import shutil
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from fastapi.security import HTTPBearer

from typing import Optional, Union
import pandas as pd # pip install pandas openpyxl

from fastapi.responses import FileResponse

from fastapi import FastAPI, Depends, status, HTTPException, File, UploadFile, Query, BackgroundTasks, Form
from sqlalchemy.orm import Session
from typing import List
import app.models as models
import app.database as database
import app.schemas as schemas
from app.auth import get_password_hash, authenticate_user, verify_refresh_token, create_access_token, create_refresh_token, get_current_user
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import ProductCreate  # Add this line
from pydantic import ValidationError


app = FastAPI()
models.Base.metadata.create_all(database.engine)

# origins = [
#     "http://localhost:3000",  # Your React app URL
#     "http://127.0.0.1:3000",
#     "http://192.168.1.20:3000",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,  # Don't use ["*"] when using credentials
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"]
# )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://http://178.62.113.250"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index():
    return {"message": "Hello, World!"}


# # Password hashing
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to validate password complexity
def validate_password(password: str) -> None:
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    if not re.search(r"[A-Za-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one letter small or capital")
    
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character")


# Start route for registering a user >>
# Route for registering a user:
@app.post("/register", response_model=schemas.UserResponse)
async def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    try:
        # Check if email already exists
        existing_user = db.query(models.Users).filter(
            models.Users.email == user.email.lower()
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Password validation is handled by Pydantic model (min_length=6)
        # Password matching is handled by Pydantic validator
        # Phone validation is handled by Pydantic validator

        # Create new user with normalized data
        db_user = models.Users(
            email=user.email.lower(),
            first_name=user.first_name.strip(),
            last_name=user.last_name.strip(),
            phone=user.phone,
            password=get_password_hash(user.password)
        )

        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
            
        except Exception as db_error:
            db.rollback()
            print(f"Database error during registration: {str(db_error)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create user account"
            )

    except HTTPException as he:
        # Re-raise HTTP exceptions with their original status codes
        raise he
    except ValueError as ve:
        # Handle validation errors from Pydantic
        raise HTTPException(
            status_code=422,
            detail=str(ve)
        )
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )

@app.post("/login", response_model=schemas.TokenResponse)
async def login(user_credentials: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    access_token_data = create_access_token({"user": user.email})
    refresh_token_data = create_refresh_token({"user": user.email})
    
    return {
        "access_token": access_token_data["token"],
        "access_token_expires": access_token_data["expires_at"],
        "refresh_token": refresh_token_data["token"],
        "refresh_token_expires": refresh_token_data["expires_at"],
        "token_type": "bearer"
    }

@app.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_token(refresh_request: schemas.RefreshTokenRequest):
    payload = verify_refresh_token(refresh_request.refresh_token)
    
    access_token_data = create_access_token({"user": payload["user"]})
    
    return {
        "access_token": access_token_data["token"],
        "access_token_expires": access_token_data["expires_at"],
        "refresh_token": refresh_request.refresh_token,
        "refresh_token_expires": datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        "token_type": "bearer"
    }

 # The end for login a user <<
    


# Route for getting all users:

@app.get("/users/me", response_model=List[schemas.UserResponse])
def fetch_users(db: Session = Depends(database.get_db)):
    users = db.query(models.Users).all()
    return users

@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def fetch_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.Users).filter(models.Users.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@app.get("/users/email/{email}", response_model=schemas.UserResponse)
def fetch_user_by_email(email: str, db: Session = Depends(database.get_db)):
    user = db.query(models.Users).filter(models.Users.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


# Route for updating a user, including password update:
@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(database.get_db)
):
    existing_user = db.query(models.Users).filter(models.Users.id == user_id).first()
    if existing_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # تحديث البيانات المقدمة فقط
    update_data = user_update.dict(exclude_unset=True)
    
    # معالجة خاصة للمة المرور إذا تم تقديمها
    if 'password' in update_data:
        update_data['password'] = get_password_hash(update_data['password'])

    for key, value in update_data.items():
        setattr(existing_user, key, value) 

    db.commit()
    db.refresh(existing_user)
    return existing_user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.Users).filter(models.Users.id == user_id).first()
    if existing_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    db.delete(existing_user)
    db.commit()
    return None

# The end for the User routes <<



@app.get("/activity", response_model=schemas.UserActivity)
def get_user_activity(
    current_user: models.Users = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    # Get recent sales (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_sales = db.query(models.Sale)\
        .filter(
            models.Sale.user_id == current_user.id,
            models.Sale.created_at >= thirty_days_ago
        )\
        .order_by(models.Sale.created_at.desc())\
        .limit(10)\
        .all()

    # Get recent products
    recent_products = db.query(models.Product)\
        .filter(models.Product.owner_id == current_user.id)\
        .order_by(models.Product.created_at.desc())\
        .limit(10)\
        .all()

    # Calculate statistics
    sales_stats = db.query(
        func.count(models.Sale.id).label('total_sales'),
        func.sum(models.Sale.total_amount).label('revenue')
    ).filter(models.Sale.user_id == current_user.id).first()

    total_products = db.query(func.count(models.Product.id))\
        .filter(models.Product.owner_id == current_user.id)\
        .scalar()

    return {
        "recent_sales": recent_sales,
        "recent_products": recent_products,
        "statistics": {
            "total_sales": sales_stats.total_sales or 0,
            "total_products": total_products or 0,
            "revenue": float(sales_stats.revenue or 0)
        }
    }



# Start Product Routes >> 
# Define base directory for the app
BASE_DIR = Path("/code/app")
UPLOAD_DIR = BASE_DIR / "uploads"

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files directory - use absolute path
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Helper function to handle file upload
async def save_upload_file(upload_file: UploadFile) -> str:
    try:
        # Generate unique filename
        file_extension = os.path.splitext(upload_file.filename)[1]
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        # Return the relative URL (this part stays the same)
        return f"/uploads/{unique_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

# Route for adding products:

# ALTER TABLE products ADD COLUMN image_url VARCHAR(255);
# @app.post("/products", status_code=status.HTTP_201_CREATED)
# async def add_product(
#     product_name: str,
#     product_price: int,
#     selling_price: int,
#     stock_quantity: int,
#     description: str = None,
#     image: UploadFile = File(None),
#     db: Session = Depends(database.get_db)
# ):
#     try:
#         # Handle image upload if provided
#         image_url = None
#         if image:
#             if not image.content_type.startswith("image/"):
#                 raise HTTPException(status_code=400, detail="File must be an image")
#             image_url = await save_upload_file(image)

#         # Create new product
#         new_product = models.Products(
#             product_name=product_name,
#             product_price=product_price,
#             selling_price=selling_price,
#             stock_quantity=stock_quantity,
#             description=description,
#             image_url=image_url
#         )
        
#         db.add(new_product)
#         db.commit()
#         db.refresh(new_product)  # Refresh to get the created_at and updated_at values
        
#         return {"message": "Product added successfully", "product": new_product}
#     except Exception as e:
#         print(f"Error adding product: {str(e)}")  # Log the error
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))

DEFAULT_IMAGE_PATH = "/uploads/default-product.jpg"  # Adjust path as needed

@app.post("/products", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
async def add_product(
    product_name: str = Query(...),
    product_price: int = Query(...),
    selling_price: int = Query(...),
    stock_quantity: int = Query(...),
    description: Optional[str] = Query(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    try:
        # Create product data dict
        product_data = {
            "product_name": product_name.strip(),
            "product_price": product_price,
            "selling_price": selling_price,
            "stock_quantity": stock_quantity,
            "description": description.strip() if description else None,
            "image_url": DEFAULT_IMAGE_PATH
        }

        # Handle image upload if provided
        if image and image.filename:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            image_url = await save_upload_file(image)
            product_data["image_url"] = image_url

        # Validate data using Pydantic model
        product_create = ProductCreate(**product_data)

        # Create new product in database
        new_product = models.Products(**product_create.dict())
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        
        return new_product

    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        print(f"Error adding product: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# @app.get("/products/check-name")  # New endpoint specifically for checking product names
# async def check_product_name(product_name: str, db: Session = Depends(database.get_db)):
#     try:
#         product = db.query(models.Products).filter(
#             models.Products.product_name == product_name
#         ).first()
#         return {"exists": product is not None}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/check-name")
async def check_product_name(product_name: str, db: Session = Depends(database.get_db)):
    try:
        # Convert to lowercase and trim whitespace for comparison
        normalized_name = product_name.lower().strip()
        product = db.query(models.Products).filter(
            func.lower(models.Products.product_name) == normalized_name
        ).first()
        
        exists = product is not None
        print(f"Checking product name: {product_name}, exists: {exists}")  # Debug log
        
        return {"exists": exists}
    except Exception as e:
        print(f"Error checking product name: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))


# Your existing routes remain unchanged
@app.get("/products")
def fetch_products(db: Session = Depends(database.get_db)):
    try:
        products = db.query(models.Products).all()
        return {"products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{id}")
def fetch_product(id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Products).filter(models.Products.id == id).first()
    if product:
        return product
    raise HTTPException(status_code=404, detail="Product not found")


@app.put("/products/{id}", status_code=status.HTTP_200_OK)
async def update_product(
    id: int,
    product_name: str = Form(...),
    product_price: float = Form(...),
    selling_price: float = Form(...),
    stock_quantity: int = Form(...),
    description: Optional[str] = Form(default=None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db)
):
    try:
        # Fetch existing product
        product = db.query(models.Products).filter(models.Products.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Check for duplicate name
        existing_product = db.query(models.Products).filter(
            models.Products.product_name == product_name.strip(),
            models.Products.id != id
        ).first()
        
        if existing_product:
            raise HTTPException(
                status_code=400,
                detail=f"Product with name '{product_name}' already exists"
            )

        # Handle image upload
        if image:
            try:
                if not image.content_type.startswith("image/"):
                    raise HTTPException(status_code=400, detail="File must be an image")
                
                # Delete old image if it exists and isn't the default
                if product.image_url and not product.image_url.endswith('default-product.png'):
                    old_image_path = os.path.join(UPLOAD_DIR, os.path.basename(product.image_url))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                image_url = await save_upload_file(image)
                product.image_url = image_url
                
            except Exception as e:
                print(f"Error handling image: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

        # Update other fields
        product.product_name = product_name.strip()
        product.product_price = float(product_price)
        product.selling_price = float(selling_price)
        product.stock_quantity = int(stock_quantity)
        if description is not None:
            product.description = description.strip()
        
        product.updated_at = datetime.utcnow()

        # Commit changes
        db.commit()
        db.refresh(product)
        
        return {
            "message": "Product updated successfully",
            "product": {
                "id": product.id,
                "product_name": product.product_name,
                "product_price": product.product_price,
                "selling_price": product.selling_price,
                "stock_quantity": product.stock_quantity,
                "description": product.description,
                "image_url": product.image_url,
                "updated_at": product.updated_at
            }
        }

    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        print(f"Error updating product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



# @app.put("/products/{id}", status_code=status.HTTP_200_OK)
# async def update_product(
#     id: int,
#     product_name: str = Query(None),
#     product_price: int = Query(None),
#     selling_price: int = Query(None),
#     stock_quantity: int = Query(None),
#     description: str = Query(None),
#     image: UploadFile = File(None),
#     image_url: str = Form(None),  # Add this parameter
#     db: Session = Depends(database.get_db)
# ):
#     try:
#         # Fetch the existing product
#         product = db.query(models.Products).filter(models.Products.id == id).first()
#         if not product:
#             raise HTTPException(status_code=404, detail="Product not found")
        
#         # Update product fields if new values are provided
#         if product_name is not None:
#             product.product_name = product_name
#         if product_price is not None:
#             product.product_price = product_price
#         if selling_price is not None:
#             product.selling_price = selling_price
#         if stock_quantity is not None:
#             product.stock_quantity = stock_quantity
#         if description is not None:
#             product.description = description
        
#         # Handle image removal
#         if image_url == '':
#             # Delete the old image file if it exists
#             if product.image_url:
#                 old_image_path = os.path.join(os.getcwd(), product.image_url.lstrip('/'))
#                 if os.path.exists(old_image_path):
#                     os.remove(old_image_path)
#             product.image_url = None
#         # Handle new image upload
#         elif image:
#             if not image.content_type.startswith("image/"):
#                 raise HTTPException(status_code=400, detail="File must be an image")
            
#             # Delete old image if exists
#             if product.image_url:
#                 old_image_path = os.path.join(os.getcwd(), product.image_url.lstrip('/'))
#                 if os.path.exists(old_image_path):
#                     os.remove(old_image_path)
            
#             # Save new image
#             image_url = await save_upload_file(image)
#             product.image_url = image_url
        
#         # Update the updated_at timestamp
#         product.updated_at = datetime.utcnow()

#         # Commit the changes to the database
#         db.commit()
#         db.refresh(product)
        
#         return {"message": "Product updated successfully", "product": product}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))
    
@app.put("/products/{id}/remove-image", status_code=status.HTTP_200_OK)
async def remove_product_image(id: int, db: Session = Depends(database.get_db)):
    try:
        product = db.query(models.Products).filter(models.Products.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Delete the physical image file if it exists
        if product.image_url:
            image_path = os.path.join(os.getcwd(), product.image_url.lstrip('/'))
            if os.path.exists(image_path):
                os.remove(image_path)

        # Update the database record
        product.image_url = None
        product.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(product)
        
        return {"message": "Image removed successfully", "product": product}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    

# Route for deleting an existing product:
@app.delete("/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(id: int, db: Session = Depends(database.get_db)):
    try:
        product = db.query(models.Products).filter(models.Products.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Delete image file if exists
        if product.image_url:
            image_path = os.path.join(os.getcwd(), product.image_url.lstrip('/'))
            if os.path.exists(image_path):
                os.remove(image_path)

        db.delete(product)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# The end for the Product routes <<



# Start Sale Routes >> 

# Route for making sales:
@app.post("/sales", status_code=status.HTTP_201_CREATED)
def add_sale(request: schemas.Sale, db: Session = Depends(database.get_db)):
    try:
        # Fetch the product
        product = db.query(models.Products).filter(models.Products.id == request.pid).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Check stock
        if product.stock_quantity < request.quantity:
            raise HTTPException(status_code=400, detail="Not enough stock available")
        
        # Create sale
        new_sale = models.Sales(
            pid=request.pid,
            quantity=request.quantity,
            user_id=request.user_id
        )
        
        db.add(new_sale)
        db.commit()
        db.refresh(new_sale)
        
        return {
            "message": "Sale created successfully",
            "sale": {
                "id": new_sale.id,
                "pid": new_sale.pid,
                "quantity": new_sale.quantity,
                "user_id": new_sale.user_id,
                "created_at": new_sale.created_at
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sales", status_code=status.HTTP_200_OK)
def fetch_sales(db: Session = Depends(database.get_db)):
    sales = db.query(models.Sales).join(models.Users).join(models.Products).all()
    return [
        {
            "id": sale.id,
            "pid": sale.pid,
            "user_id": sale.user_id,
            "first_name": sale.users.first_name,
            "quantity": sale.quantity,
            "created_at": sale.created_at,
            "product_name": sale.products.product_name, 
            "product_price": sale.products.product_price,
            "total_amount": sale.quantity * sale.products.product_price
        }
        for sale in sales
    ]


# Route for getting sale by the sale id:
@app.get("/sales/{id}", status_code=status.HTTP_200_OK)
def fetch_sale(id: int, db: Session = Depends(database.get_db)):
    sale = (
        db.query(models.Sales)
        .join(models.Users)
        .join(models.Products)
        .filter(models.Sales.id == id)
        .first()
    )
    
    if sale:
        total_amount = sale.quantity * sale.products.product_price  # Calculate total amount
        return {
            "id": sale.id,
            "pid": sale.pid,
            "user_id": sale.users.id, 
            "product_name": sale.products.product_name,
            "quantity": sale.quantity, 
            "created_at": sale.created_at,
            "total_amount": total_amount  # Include total amount in the response
        }
    
    raise HTTPException(status_code=404, detail="Sale not found")

# Route for getting sales by user ID:
@app.get("/sales/user/{user_id}", status_code=status.HTTP_200_OK)
def fetch_sales_by_user(user_id: int, db: Session = Depends(database.get_db)):
    sales = db.query(models.Sales).join(models.Users).join(models.Products).filter(models.Sales.user_id == user_id).all()
    
    if not sales:
        raise HTTPException(status_code=404, detail="No sales found for this user")
    
    return [{
        "id": sale.id,
        "pid": sale.pid,
        "user_id": sale.user_id,
        "first_name": sale.users.first_name,
        "quantity": sale.quantity,
        "created_at": sale.created_at,  # Include created_at in the response
        "total_amount": sale.quantity * sale.products.product_price  # Calculate total amount
    } for sale in sales]
    

# Route for updating sales:
@app.put("/sales/{id}", status_code=status.HTTP_202_ACCEPTED)
def update_sale(id: int, request: schemas.UpdateSale, db: Session = Depends(database.get_db)):
    try:
        # Print request data for debugging
        print(f"Updating sale {id} with data:", request)
        
        # Fetch the existing sale
        sale = db.query(models.Sales).filter(models.Sales.id == id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        print(f"Found existing sale:", sale.__dict__)

        # Fetch the corresponding product
        product = db.query(models.Products).filter(models.Products.id == request.pid).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        print(f"Found product:", product.__dict__)

        # Calculate the difference in quantity
        quantity_difference = request.quantity - sale.quantity
        print(f"Quantity difference:", quantity_difference)

        # Validate stock quantity
        if product.stock_quantity - quantity_difference < 0:
            raise HTTPException(
                status_code=400,
                detail="Not enough stock available"
            )

        # Update the sale details
        sale.quantity = request.quantity
        sale.user_id = request.user_id
        sale.price = request.price
        sale.date = request.date
        sale.pid = request.pid

        # Update the product's stock quantity
        product.stock_quantity -= quantity_difference

        # Commit the changes
        db.commit()
        
        return {
            "message": "Sale updated successfully",
            "sale": {
                "id": sale.id,
                "quantity": sale.quantity,
                "price": sale.price,
                "date": sale.date,
                "user_id": sale.user_id,
                "pid": sale.pid
            }
        }
    except Exception as e:
        db.rollback()  # Rollback changes if there's an error
        print(f"Error updating sale: {str(e)}")  # Print the error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update sale: {str(e)}"
        )


# Route for deleting a sale:
@app.delete("/sales/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(sale_id: int, db: Session = Depends(database.get_db)):
    existing_sale = db.query(models.Sales).filter(models.Sales.id == sale_id).first()  # Fetch sale by ID
    if existing_sale is None:
        raise HTTPException(status_code=404, detail="Sale not found") 
    product = db.query(models.Products).filter(models.Products.id == existing_sale.pid).first()
    if product:
        product.stock_quantity += existing_sale.quantity  # Restore stock quantity if needed

    db.delete(existing_sale)  # Delete the sale from the database
    db.commit()  # Commit the deletion to the database
    return  # Return nothing for 204 No Content

# The end for the Sale routes <<

# Start contact Routes >> 

@app.post("/contact", response_model=schemas.ContactResponse)
async def create_contact(
    contact: schemas.ContactCreate,
    db: Session = Depends(database.get_db)
):
    try:
        new_contact = models.Contact(**contact.dict())
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
        return new_contact
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/contact/{contact_id}/reply", response_model=schemas.ContactResponse)
async def reply_to_contact(
    contact_id: int,
    reply_data: schemas.ReplyCreate,
    db: Session = Depends(database.get_db)
):
    try:
        # Find the contact message
        contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact message not found")
        
        # Update contact with reply
        contact.response = reply_data.reply
        contact.status = "closed"
        contact.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(contact)
        
        return contact
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contact", response_model=List[schemas.ContactResponse])
async def get_contacts(
    db: Session = Depends(database.get_db),
):
    contacts = db.query(models.Contact).order_by(
        models.Contact.created_at.desc()
    )
    return contacts

@app.get("/contact/{contact_id}", response_model=schemas.ContactResponse)
async def get_contact(contact_id: int, db: Session = Depends(database.get_db)):
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@app.put("/contact/{contact_id}/status")
async def update_contact_status(
    contact_id: int,
    status_data: dict,
    db: Session = Depends(database.get_db)
):
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    contact.status = status_data.get("status")
    db.commit()
    return contact

@app.delete("/contact/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(database.get_db)
):
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    db.delete(contact)
    db.commit()
    return {"message": "Contact deleted successfully"}

# The end for the Contact routes <<



@app.post("/import/products")
async def import_products(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: Optional[int] = None
):
    # Create import history record
    import_record = models.ImportHistory(
        filename=file.filename,
        status='processing',
        user_id=current_user
    )
    db.add(import_record)
    db.commit()

    try:
        # Read file content
        content = await file.read()
        
        # Process based on file type
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Please upload CSV or Excel file."
            )

        # Update import record with total rows
        import_record.total_rows = len(df)
        db.commit()

        # Process records
        success_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Check if product already exists
                existing_product = db.query(models.Products).filter(
                    models.Products.product_name == row['product_name']
                ).first()

                if existing_product:
                    # Update existing product
                    existing_product.product_price = row['product_price']
                    existing_product.selling_price = row['selling_price']
                    existing_product.stock_quantity = row['stock_quantity']
                    if 'description' in row:
                        existing_product.description = row['description']
                else:
                    # Create new product
                    new_product = models.Products(
                        product_name=row['product_name'],
                        product_price=row['product_price'],
                        selling_price=row['selling_price'],
                        stock_quantity=row['stock_quantity'],
                        description=row.get('description', None)
                    )
                    db.add(new_product)
                
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    'row': index + 2,
                    'product_name': row['product_name'],
                    'error': str(e)
                })

        # Update import record with results
        import_record.status = 'completed'
        import_record.successful_rows = success_count
        import_record.failed_rows = error_count
        import_record.errors = errors
        import_record.completed_at = datetime.now()
        
        # Commit all changes
        db.commit()

        return {
            "import_id": import_record.id,
            "message": "Import completed",
            "total_processed": len(df),
            "successful": success_count,
            "failed": error_count,
            "errors": errors if errors else None
        }

    except Exception as e:
        # Update import record with error status
        import_record.status = 'failed'
        import_record.errors = [{"error": str(e)}]
        import_record.completed_at = datetime.now()
        db.commit()
        
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/import/template/{file_type}")
async def get_import_template(file_type: str, background_tasks: BackgroundTasks):
    if file_type not in ['csv', 'excel']:
        raise HTTPException(status_code=400, detail="Invalid template type")
    
    # Create sample data
    data = {
        'product_name': ['Sample Product 1', 'Sample Product 2'],
        'product_price': [100, 200],
        'selling_price': [150, 250],
        'stock_quantity': [50, 75],
        'description': ['Sample description 1', 'Sample description 2']
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create temporary file
    temp_file = f"temp_template.{'xlsx' if file_type == 'excel' else 'csv'}"
    
    # Save template
    if file_type == 'excel':
        df.to_excel(temp_file, index=False)
    else:
        df.to_csv(temp_file, index=False)
    
    # Add cleanup task
    background_tasks.add_task(os.remove, temp_file)
    
    # Return file
    return FileResponse(
        path=temp_file,
        filename=f"product_import_template.{'xlsx' if file_type == 'excel' else 'csv'}",
        media_type='application/octet-stream'
    )

# Add this utility endpoint to validate file before import
@app.post("/import/products/validate")
async def validate_import_file(
    file: UploadFile = File(...)
):
    try:
        content = await file.read()
        
        # Process based on file type
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Please upload CSV or Excel file."
            )

        # Validate required columns
        required_columns = ['product_name', 'product_price', 'selling_price', 'stock_quantity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                "valid": False,
                "errors": f"Missing required columns: {', '.join(missing_columns)}"
            }

        # Validate data types and values
        errors = []
        for index, row in df.iterrows():
            row_errors = []
            
            # Validate product name
            if not row['product_name'] or pd.isna(row['product_name']):
                row_errors.append("Product name is required")
            
            # Validate prices and quantity
            for field in ['product_price', 'selling_price', 'stock_quantity']:
                try:
                    value = float(row[field])
                    if value < 0:
                        row_errors.append(f"{field} cannot be negative")
                except (ValueError, TypeError):
                    row_errors.append(f"Invalid {field}")
            
            if row_errors:
                errors.append({
                    "row": index + 2,
                    "product_name": row['product_name'],
                    "errors": row_errors
                })

        return {
            "valid": len(errors) == 0,
            "total_rows": len(df),
            "errors": errors if errors else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add endpoints to view import history
@app.get("/import/history")
async def get_import_history(
    db: Session = Depends(database.get_db),
    skip: int = 0,
    limit: int = 10
):
    imports = db.query(models.ImportHistory)\
        .order_by(models.ImportHistory.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return imports

@app.get("/import/history/{import_id}")
async def get_import_details(
    import_id: int,
    db: Session = Depends(database.get_db)
):
    import_record = db.query(models.ImportHistory)\
        .filter(models.ImportHistory.id == import_id)\
        .first()
    
    if not import_record:
        raise HTTPException(status_code=404, detail="Import record not found")
    
    return import_record





















    
    



