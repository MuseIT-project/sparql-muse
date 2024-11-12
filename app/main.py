# app/main.py
from fastapi import FastAPI, Response, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from utils import buildgraph, autosuggest, getpredicates
import json
from fastapi import Query
import jwt
from jose import JWTError
import logging
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Get environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # Default to HS256 if not specified

# Verify SECRET_KEY is set
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")

app = FastAPI()

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Define token model
class TokenData(BaseModel):
    email: str
    google_token: str
    token_type: str = "Bearer"

# Security scheme for JWT
security = HTTPBearer(auto_error=False)

# JWT validation function that allows None
async def verify_jwt(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:  # Allow requests without token
        return None
    try:
        token = credentials.credentials
        # For debugging
        logging.error(f"Received token: {token[:20]}...")  # Show first 20 chars
        
        if token == "undefined" or not token:  # Handle undefined or empty token
            return None
            
        # Try to decode as regular JWT first
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            logging.error(f"Decoded payload: {payload}")  # Debug log
            return {
                "token": token,
                "token_type": "Bearer",
                "email": payload.get("email")  # Extract email from JWT payload
            }
        except Exception as e:
            logging.error(f"JWT decode error: {str(e)}")  # Debug log
            # If regular JWT decode fails, assume it's the raw Google token
            return {
                "token": token,
                "token_type": "Bearer",
                "email": None
            }
            
    except Exception as e:
        logging.error(f"Token verification error: {str(e)}")
        return None

@app.post("/token")
async def create_token(token_data: TokenData):
    return {
        "access_token": token_data.google_token,
        "token_type": "Bearer"
    }

@app.get("/")
async def root(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    q: str = Query(default=None),
    subject: str = Query(default=None, description="Subject of the triple"),
    predicate: str = Query(default=None, description="Predicate of the triple"),
    object: str = Query(default=None, description="Object of the triple"),
    suggest: str = Query(default=None, description="Use autosuggest instead of graph"),
    field: list[str] = Query(default=None, description="List of fields to search in")
):
    try:
        # Get user info from JWT, will be None for unauthenticated users
        user_info = await verify_jwt(auth)
        
        inputparams = {
            "q": q,
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "suggest": suggest,
            "field": field,
            "email": user_info.get("email") if user_info else None  # Will be None for unauthenticated users
        }
        
        if suggest:
            result = autosuggest(inputparams)
        else:
            result = buildgraph(inputparams)
            
        return Response(
            json.dumps(result, indent=4),
            media_type="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    except Exception as e:
        logging.error(f"Error in root endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/predicate")
async def get_predicates(auth: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    verify_jwt(auth)  # Optional verification
    return Response(
        json.dumps(getpredicates(), indent=4),
        media_type="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )

class TokenRequest(BaseModel):
    google_token: str
    email: Optional[str] = None
    token_type: Optional[str] = "Bearer"

@app.post("/auth/token")
async def auth_token(request: TokenRequest):
    try:
        logging.error(f"Token request: {request}")  # Debug log
        
        if not request.google_token or request.google_token == "undefined":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token provided"
            )
            
        # Create a JWT with the email
        token_data = {
            "email": request.email,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        jwt_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        logging.error(f"Created JWT token: {jwt_token[:20]}...")  # Debug log
        logging.error(f"Token data: {token_data}")  # Debug log
        
        return Response(
            json.dumps({
                "access_token": jwt_token,  # Send JWT instead of raw Google token
                "token_type": "Bearer",
                "email": request.email
            }, indent=4),
            media_type="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    except Exception as e:
        logging.error(f"Token creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

