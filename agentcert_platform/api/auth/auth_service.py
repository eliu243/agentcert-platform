"""
Authentication service for GitHub OAuth and session management
"""

import os
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from authlib.integrations.httpx_client import AsyncOAuth2Client
import httpx

logger = logging.getLogger(__name__)

# Configuration from environment variables
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/api/auth/callback")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

# GitHub OAuth endpoints
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API = "https://api.github.com/user"
GITHUB_REPOS_API = "https://api.github.com/user/repos"


class AuthService:
    """Service for handling authentication and GitHub OAuth"""
    
    def __init__(self):
        """Initialize authentication service"""
        # In-memory session storage: user_id -> session_data
        self.sessions: Dict[str, Dict[str, Any]] = {}
        # In-memory token storage: token -> user_id (for quick lookup)
        self.token_to_user: Dict[str, str] = {}
        
        # OAuth client
        self.oauth_client = AsyncOAuth2Client(
            client_id=GITHUB_CLIENT_ID,
            client_secret=GITHUB_CLIENT_SECRET,
            redirect_uri=GITHUB_CALLBACK_URL,
        )
        
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate GitHub OAuth authorization URL"""
        if not GITHUB_CLIENT_ID:
            raise ValueError("GITHUB_CLIENT_ID not configured")
        
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": GITHUB_CALLBACK_URL,
            "scope": "read:user user:email repo",  # Request repo access
        }
        
        if state:
            params["state"] = state
        
        # Build authorization URL
        from urllib.parse import urlencode
        return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token"""
        if not GITHUB_CLIENT_SECRET:
            raise ValueError("GITHUB_CLIENT_SECRET not configured")
        
        try:
            # Exchange code for token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GITHUB_TOKEN_URL,
                    data={
                        "client_id": GITHUB_CLIENT_ID,
                        "client_secret": GITHUB_CLIENT_SECRET,
                        "code": code,
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                token_data = response.json()
                access_token = token_data.get("access_token")
                
                if not access_token:
                    raise ValueError("No access token received from GitHub")
                
                # Fetch user info from GitHub
                user_response = await client.get(
                    GITHUB_USER_API,
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                user_response.raise_for_status()
                user_data = user_response.json()
                
                return {
                    "access_token": access_token,
                    "user_id": str(user_data["id"]),
                    "github_username": user_data["login"],
                    "github_name": user_data.get("name"),
                    "github_email": user_data.get("email"),
                    "avatar_url": user_data.get("avatar_url"),
                }
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            raise
    
    def create_session(self, user_data: Dict[str, Any]) -> str:
        """Create a session and return JWT token"""
        user_id = user_data["user_id"]
        github_username = user_data["github_username"]
        access_token = user_data["access_token"]
        
        # Create JWT token
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=SESSION_EXPIRY_HOURS)
        token_data = {
            "sub": user_id,  # Subject (user ID)
            "github_username": github_username,
            "exp": int(expires_at.timestamp()),  # JWT exp expects Unix timestamp
            "iat": int(now.timestamp()),  # JWT iat expects Unix timestamp
        }
        
        token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store session
        session_data = {
            "user_id": user_id,
            "github_username": github_username,
            "github_name": user_data.get("github_name"),
            "github_email": user_data.get("github_email"),
            "avatar_url": user_data.get("avatar_url"),
            "access_token": access_token,
            "token": token,
            "expires_at": expires_at.timestamp(),
            "created_at": time.time(),
        }
        
        self.sessions[user_id] = session_data
        self.token_to_user[token] = user_id
        
        logger.info(f"Created session for user {github_username} ({user_id})")
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return user data"""
        try:
            # Decode token
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            
            if not user_id:
                return None
            
            # Check if session exists
            session = self.sessions.get(user_id)
            if not session:
                return None
            
            # Check if token matches
            if session.get("token") != token:
                return None
            
            # Check if expired
            if session.get("expires_at", 0) < time.time():
                # Clean up expired session
                self.delete_session(user_id)
                return None
            
            return {
                "user_id": user_id,
                "github_username": session.get("github_username"),
                "github_name": session.get("github_name"),
                "github_email": session.get("github_email"),
                "avatar_url": session.get("avatar_url"),
            }
        except JWTError as e:
            logger.warning(f"JWT validation error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return None
    
    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session data for a user"""
        return self.sessions.get(user_id)
    
    def delete_session(self, user_id: str) -> None:
        """Delete a user session"""
        session = self.sessions.get(user_id)
        if session:
            token = session.get("token")
            if token and token in self.token_to_user:
                del self.token_to_user[token]
            del self.sessions[user_id]
            logger.info(f"Deleted session for user {user_id}")
    
    async def get_user_repositories(self, access_token: str, per_page: int = 100) -> list:
        """Fetch user's GitHub repositories"""
        try:
            repos = []
            page = 1
            
            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        GITHUB_REPOS_API,
                        params={
                            "per_page": per_page,
                            "page": page,
                            "sort": "updated",
                            "direction": "desc",
                        },
                        headers={
                            "Authorization": f"token {access_token}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                    )
                    response.raise_for_status()
                    page_repos = response.json()
                    
                    if not page_repos:
                        break
                    
                    # Format repos
                    for repo in page_repos:
                        repos.append({
                            "id": repo["id"],
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "description": repo.get("description"),
                            "private": repo["private"],
                            "html_url": repo["html_url"],
                            "clone_url": repo["clone_url"],
                            "ssh_url": repo.get("ssh_url"),
                            "default_branch": repo.get("default_branch", "main"),
                            "updated_at": repo.get("updated_at"),
                        })
                    
                    # Check if there are more pages
                    if len(page_repos) < per_page:
                        break
                    
                    page += 1
            
            logger.info(f"Fetched {len(repos)} repositories")
            return repos
        except Exception as e:
            logger.error(f"Error fetching repositories: {e}")
            raise


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get or create auth service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service

