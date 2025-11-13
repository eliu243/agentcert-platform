"""
Authentication dependencies for FastAPI routes
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
from .auth_service import get_auth_service

# HTTP Bearer token security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.
    
    Returns:
        Dict with user information (user_id, github_username, etc.)
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    auth_service = get_auth_service()
    
    user = auth_service.validate_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication dependency - returns user if authenticated, None otherwise.
    
    Use this for endpoints that work with or without authentication.
    
    Returns:
        Dict with user information if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        auth_service = get_auth_service()
        user = auth_service.validate_token(token)
        return user
    except:
        return None

