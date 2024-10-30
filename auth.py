from passlib.context import CryptContext
from models import Users
from database import sessionLocal
from datetime import timedelta, datetime, timezone
from jose import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status

SECRET_KEY = "ec998ae8f46bc6a0b20726acfe452ca6b63c3559e215c9260187b3ae902edd70"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def check_user(email):
    db = sessionLocal()
    user = db.query(Users).filter(Users.email == email).first()
    return user

def create_token(data:dict, expires_delta:timedelta | None=None):
    to_encode = data.copy()
    if expires_delta:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + expires_delta(minutes=30)
    to_encode.update({"exp":expires})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, ALGORITHM)
    return encoded_jwt

def get_token_auth_headers(credentials:HTTPAuthorizationCredentials=Depends(HTTPBearer())):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")
    return credentials.credentials

def get_current_user(token:str = Depends(get_token_auth_headers)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("user")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token ")
    user = check_user(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User does not exist ")
    return user





    
        


        


