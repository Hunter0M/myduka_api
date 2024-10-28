import re # Pattern Matching: Regular expressions allow you to define a search pattern. This pattern can be used to check if a string contains specific characters, words, or sequences.

from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, database,schemas
# this for hashing the password
from passlib.context import CryptContext # pip install passlib[bcrypt] 

app = FastAPI()
models.Base.metadata.create_all(database.engine)


@app.get("/")
def index():
    return {"message": "Hello, World!"}


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
@app.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.User, db: Session = Depends(database.get_db)):
    # Check if passwords match
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Validate password complexity
    validate_password(user.password)

    # Check if the user already exists
    existing_user = db.query(models.Users).filter(models.Users.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password
    hashed_password = pwd_context.hash(user.password)

    # Create a new user instance
    new_user = models.Users(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        password=hashed_password  # Store the hashed password
        # Note: Do not store confirm_password in the database
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User  registered successfully", "user_id": new_user.id}
# The end for registering a user <<


# Route for getting all users
@app.get("/users", response_model=List[schemas.UserResponse])
def fetch_users(db: Session = Depends(database.get_db)):
    users = db.query(models.Users).all()  # Fetch all users from the database
    return users


# Route for getting a user by ID:
@app.get("/users/{user_id}", response_model=schemas.UserResponse)  # Adjust the response model as needed
def fetch_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.Users).filter(models.Users.id == user_id).first()  # Fetch user by ID
    if user is None:
        raise HTTPException(status_code=404, detail="User  not found")  # Raise error if user not found
    return user

# The end for the User routes <<

# Login route
@app.post("/login", response_model=dict)
def login(user: schemas.UserLogin, db: Session = Depends(database.get_db)):
    # Fetch the user by email
    existing_user = db.query(models.Users).filter(models.Users.email == user.email).first()
    
    # Check if user exists
    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # Verify the password
    if not pwd_context.verify(user.password, existing_user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    return {"message": "Login successful", "user_id": existing_user.id}

# Start Product Routes >> 

# Route for adding products:
@app.post("/products", status_code=status.HTTP_201_CREATED)
def add_product(request:schemas.Product, db:Session=Depends(database.get_db)):
    new_product = models.Products(product_name=request.product_name, product_price=request.product_price, selling_price=request.selling_price, stock_quantity=request.stock_quantity)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"message":"Product added successfully"}

# Route for getting products:
@app.get("/products", status_code=status.HTTP_200_OK)
def fetch_products(db:Session=Depends(database.get_db)):
    products= db.query(models.Products).all()
    return products

# Route for getting product by the product id: 
@app.get("/products/{id}", status_code=status.HTTP_200_OK)
def fetch_product(id, db:Session=Depends(database.get_db)):
    product = db.query(models.Products).filter(models.Products.id == id).first()
    if product:
        return product

# Route for updatting an existing product:
@app.put("/products/{id}", status_code=status.HTTP_202_ACCEPTED)
def update_product(id, request:schemas.Product, db:Session=Depends(database.get_db)):
    product = db.query(models.Products).filter(models.Products.id == id).first()
    if product:
        product.product_name = request.product_name
        product.product_price = request.product_price
        product.selling_price = request.selling_price
        product.stock_quantity = request.stock_quantity
        db.commit()
        return {"message": "Product updated successfully"}
    

# Route for deleting an existing product:
@app.delete("/products/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(id, db:Session=Depends(database.get_db)):
    product = db.query(models.Products).filter(models.Products.id == id).first()
    if product:
        db.delete(product)
        db.commit()  # Commit the deletion to the database
        return  # Return nothing for 204 No Content
    return {"error": "Product not found"}, status.HTTP_404_NOT_FOUND  # Optional: handle case where product is not found

# The end for the Product routes <<



# Start Sale Routes >> 

# Route for making sales:
@app.post("/sales", status_code=status.HTTP_201_CREATED)
def add_sale(request: schemas.Sale, db: Session = Depends(database.get_db)):
    # Fetch the product to check its stock quantity
    product = db.query(models.Products).filter(models.Products.id == request.pid).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if the user exists
    user = db.query(models.Users).filter(models.Users.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User  not found")

    if product.stock_quantity < request.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock available")
    
    # Create a new sale instance
    new_sale = models.Sales(pid=request.pid, user_id=request.user_id, quantity=request.quantity)
    
    # Update the stock quantity of the product
    product.stock_quantity -= request.quantity
    
    # Add the new sale and commit the changes
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)
    
    # Refresh the product to reflect the updated stock quantity
    db.commit()  # Commit the changes to the product
    
    return {"message": "Sale added successfully", "sale_id": new_sale.id}


# Route for getting sales:
@app.get("/sales", status_code=status.HTTP_200_OK)
def fetch_sales(db: Session = Depends(database.get_db)):
    sales = db.query(models.Sales).join(models.Users).all()
    return [{"id": sale.id, "pid": sale.pid, "user_id": sale.user_id, "first name": sale.users.first_name, "quantity": sale.quantity} for sale in sales]


# Route for getting sale by the sale id:
@app.get("/sales/{id}", status_code=status.HTTP_200_OK)
def fetch_sale(id: int, db: Session = Depends(database.get_db)):
    sale = (
        db.query(models.Sales).join(models.Users).join(models.Products).filter(models.Sales.id == id).first()
    )
    if sale:
        return {
            "id": sale.id,
            "pid": sale.pid,
            "user_id": sale.users.id, 
            "product_name": sale.products.name,
            "quantity": sale.quantity
        }
    raise HTTPException(status_code=404, detail="Sale not found")
    


# Route for updating sales
@app.put("/sales/{id}", status_code=status.HTTP_202_ACCEPTED)
def update_sale(id: int, request: schemas.Sale, db: Session = Depends(database.get_db)):
    # Fetch the existing sale
    sale = db.query(models.Sales).filter(models.Sales.id == id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    # Fetch the corresponding product
    product = db.query(models.Products).filter(models.Products.id == sale.pid).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Calculate the difference in quantity
    quantity_difference = request.quantity - sale.quantity

    # Update the sale quantity
    sale.quantity = request.quantity

    # Update the product's stock quantity
    product.stock_quantity -= quantity_difference

    # Commit the changes
    db.commit()
    
    return {"message": "Sale updated successfully"}


# Route for getting sales by user ID:
@app.get("/sales/user/{user_id}", status_code=status.HTTP_200_OK)
def fetch_sales_by_user(user_id: int, db: Session = Depends(database.get_db)):
    sales = db.query(models.Sales).filter(models.Sales.user_id == user_id).join(models.Users).all()
    
    if not sales:
        raise HTTPException(status_code=404, detail="No sales found for this user")
    
    return [{
        "id": sale.id,
        "pid": sale.pid,
        "user_id": sale.user_id,
        "first_name": sale.users.first_name,
        "quantity": sale.quantity
    } for sale in sales]

# The end for the Sale routes <<


















    
    



