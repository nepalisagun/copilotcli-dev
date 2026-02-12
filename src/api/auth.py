"""Authentication and authorization for API."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


class TokenManager:
    """Manage JWT tokens."""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None


async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    """Get current authenticated user from token."""
    token = credentials.credentials
    payload = TokenManager.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user information",
        )
    
    return {"user_id": user_id, "scopes": payload.get("scopes", [])}


class RoleBasedAccess:
    """Role-based access control."""
    
    ROLES = {
        "admin": ["read", "write", "delete"],
        "user": ["read"],
        "contributor": ["read", "write"]
    }
    
    @staticmethod
    def check_role(required_role: str, user_role: str) -> bool:
        """Check if user role has required role."""
        user_scopes = RoleBasedAccess.ROLES.get(user_role, [])
        required_scopes = RoleBasedAccess.ROLES.get(required_role, [])
        return any(scope in user_scopes for scope in required_scopes)
    
    @staticmethod
    async def require_role(required_role: str, current_user: dict = Depends(get_current_user)) -> dict:
        """Dependency to check user role."""
        user_role = current_user.get("role")
        
        if not user_role or not RoleBasedAccess.check_role(required_role, user_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
