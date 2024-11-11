import re # Pattern Matching: Regular expressions allow you to define a search pattern. This pattern can be used to check if a string contains specific characters, words, or sequences.
import os
import io
from fastapi.staticfiles import StaticFiles
import shutil
from uuid import uuid4
from datetime import datetime,timezone
from fastapi.security import HTTPBearer

from typing import Optional
import pandas as pd # pip install pandas openpyxl

from fastapi.responses import FileResponse

from fastapi import FastAPI, Depends, status, HTTPException, File, UploadFile, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import models, database,schemas
from auth import get_password_hash, authenticate_user, verify_refresh_token,create_access_token, create_refresh_token
# # this for hashing the password
# from passlib.context import CryptContext # pip install passlib[bcrypt] 
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
models.Base.metadata.create_all(database.engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
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
    # التحقق من وجود المستخدم
    if db.query(models.Users).filter(models.Users.email == user.email).first():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # إنشاء مستخدم جديد
    db_user = models.Users(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        password=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

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

@app.get("/users", response_model=List[schemas.UserResponse])
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
    
    # معالجة خاصة لكلمة المرور إذا تم تقديمها
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



# Start Product Routes >> 

# Create uploads directory if it doesn't exist
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files directory after creating it
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Helper function to handle file upload
async def save_upload_file(upload_file: UploadFile) -> str:
    try:
        # Generate unique filename
        file_extension = os.path.splitext(upload_file.filename)[1]
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        # Return the relative URL
        return f"/uploads/{unique_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

# Route for adding products:

# ALTER TABLE products ADD COLUMN image_url VARCHAR(255);
@app.post("/products", status_code=status.HTTP_201_CREATED)
async def add_product(
    product_name: str,
    product_price: int,
    selling_price: int,
    stock_quantity: int,
    description: str = None,
    image: UploadFile = File(None),
    db: Session = Depends(database.get_db)
):
    try:
        # Handle image upload if provided
        image_url = None
        if image:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            image_url = await save_upload_file(image)

        # Create new product
        new_product = models.Products(
            product_name=product_name,
            product_price=product_price,
            selling_price=selling_price,
            stock_quantity=stock_quantity,
            description=description,
            image_url=image_url
        )
        
        db.add(new_product)
        db.commit()
        db.refresh(new_product)  # Refresh to get the created_at and updated_at values
        
        return {"message": "Product added successfully", "product": new_product}
    except Exception as e:
        print(f"Error adding product: {str(e)}")  # Log the error
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/products/check-name")  # New endpoint specifically for checking product names
async def check_product_name(product_name: str, db: Session = Depends(database.get_db)):
    try:
        product = db.query(models.Products).filter(
            models.Products.product_name == product_name
        ).first()
        return {"exists": product is not None}
    except Exception as e:
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



# Route for getting products:
# @app.get("/products", )
# def fetch_products(db: Session = Depends(database.get_db)):
#     try:
#         products = db.query(models.Products).all()  # Fetch all products from the database
#         return {"products":products}  # Return the list of products
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))  

# # Route for getting product by the product id: 
# @app.get("/products/{id}", status_code=status.HTTP_200_OK)
# def fetch_product(id: int, db: Session = Depends(database.get_db)):
#     product = db.query(models.Products).filter(models.Products.id == id).first()
#     if product:
#         return product
#     raise HTTPException(status_code=404, detail="Product not found")


# Route for update product : 
@app.put("/products/{id}", status_code=status.HTTP_200_OK)
async def update_product(
    id: int,
    product_name: str = Query(None),
    product_price: int = Query(None),
    selling_price: int = Query(None),
    stock_quantity: int = Query(None),
    description: str = Query(None),
    image: UploadFile = File(None),
    db: Session = Depends(database.get_db)
):
    try:
        # Fetch the existing product
        product = db.query(models.Products).filter(models.Products.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Update product fields if new values are provided
        if product_name is not None:
            product.product_name = product_name
        if product_price is not None:
            product.product_price = product_price
        if selling_price is not None:
            product.selling_price = selling_price
        if stock_quantity is not None:
            product.stock_quantity = stock_quantity
        if description is not None:
            product.description = description
        
        # Handle image upload if provided
        if image:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            # Save the new image and update the image_url
            image_url = await save_upload_file(image)
            product.image_url = image_url
        
        # Update the updated_at timestamp
        product.updated_at = datetime.utcnow()  # or use func.now() if using SQLAlchemy

        # Commit the changes to the database
        db.commit()
        db.refresh(product)
        
        return {"message": "Product updated successfully", "product": product}
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
    # Fetch the product to check its stock quantity
    product = db.query(models.Products).filter(models.Products.id == request.pid).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock_quantity < request.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock available")
    
    # Create a new sale instance with user_id
    new_sale = models.Sales(
        pid=request.pid, 
        quantity=request.quantity,
        user_id=request.user_id  # Add this line
    )
    
    # Update the stock quantity of the product
    product.stock_quantity -= request.quantity
    
    # Add the new sale and commit the changes
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)
    
    return {"message": "Sale added successfully", "sale_id": new_sale.id}


# Route for getting sales:
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
            "total_amount": sale.quantity * sale.products.product_price  # Calculate total amount
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





















    
    



