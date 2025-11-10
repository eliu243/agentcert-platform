"""
Authentication API routes
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from typing import Dict, Any
import secrets
import os

from ..auth.auth_service import get_auth_service
from ..auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/auth/login")
async def login(state: str = Query(None)):
    """
    Initiate GitHub OAuth login flow.
    Redirects user to GitHub authorization page.
    """
    try:
        auth_service = get_auth_service()
        
        # Generate state for CSRF protection if not provided
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Get authorization URL
        auth_url = auth_service.get_authorization_url(state=state)
        
        # Redirect to GitHub
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Error initiating login: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate login: {str(e)}")


@router.get("/auth/callback")
async def callback(code: str = Query(...), state: str = Query(None)):
    """
    Handle GitHub OAuth callback.
    Exchanges code for token and creates session.
    Redirects to frontend with token.
    """
    try:
        auth_service = get_auth_service()
        
        # Exchange code for token
        user_data = await auth_service.exchange_code_for_token(code)
        
        # Create session
        token = auth_service.create_session(user_data)
        
        # Redirect to frontend with token
        # Frontend will handle storing the token
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        
        # URL encode the token to handle special characters
        from urllib.parse import urlencode
        redirect_url = f"{frontend_url}/?{urlencode({'token': token})}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        # Redirect to frontend with error
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        from urllib.parse import urlencode
        redirect_url = f"{frontend_url}/?{urlencode({'error': str(e)})}"
        return RedirectResponse(url=redirect_url)


@router.get("/auth/me")
async def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current user information.
    """
    return {
        "user_id": user["user_id"],
        "github_username": user["github_username"],
        "github_name": user.get("github_name"),
        "github_email": user.get("github_email"),
        "avatar_url": user.get("avatar_url"),
    }


@router.get("/auth/repos")
async def get_repos(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get user's GitHub repositories.
    """
    try:
        auth_service = get_auth_service()
        session = auth_service.get_session(user["user_id"])
        
        if not session:
            raise HTTPException(status_code=401, detail="Session not found")
        
        access_token = session.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Access token not found")
        
        # Fetch repositories
        repos = await auth_service.get_user_repositories(access_token)
        
        return {
            "repos": repos,
            "count": len(repos),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repositories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")


@router.post("/auth/logout")
async def logout(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Logout current user and invalidate session.
    """
    try:
        auth_service = get_auth_service()
        auth_service.delete_session(user["user_id"])
        
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error logging out: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to logout: {str(e)}")

