from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt_utils import jwt_handler
from app.db import db_manager
from bson import ObjectId
import jwt as pyjwt
from typing import Dict

security = HTTPBearer()

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    Dependency to get current authenticated admin from JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Dictionary containing admin and organization info
        
    Raises:
        HTTPException: If token is invalid or admin not found
    """
    token = credentials.credentials
    
    try:
        # Decode token
        payload = jwt_handler.decode_token(token)
        admin_id = payload.get("admin_id")
        organization_id = payload.get("organization_id")
        
        if not admin_id or not organization_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Verify admin exists in database
        master_db = db_manager.get_master_db()
        admin = master_db.admins.find_one({"_id": ObjectId(admin_id)})
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin not found"
            )
        
        # Verify organization exists
        organization = master_db.organizations.find_one({"_id": ObjectId(organization_id)})
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Organization not found"
            )
        
        return {
            "admin_id": str(admin["_id"]),
            "email": admin["email"],
            "organization_id": str(organization["_id"]),
            "organization_name": organization["organization_name"],
            "collection_name": organization["collection_name"]
        }
        
    except pyjwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )