from fastapi import APIRouter, HTTPException, status
from app.models.schemas import AdminLogin, LoginResponse
from app.db import db_manager
from app.auth.hashing import password_hasher
from app.auth.jwt_utils import jwt_handler
from bson import ObjectId

router = APIRouter(prefix="/admin", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def admin_login(login_data: AdminLogin):
    """
    Admin login endpoint
    
    - Validates admin credentials
    - Returns JWT access token
    """
    try:
        master_db = db_manager.get_master_db()
        
        # Find admin by email
        admin = master_db.admins.find_one({"email": login_data.email})
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not password_hasher.verify_password(login_data.password, admin["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get organization details
        organization = master_db.organizations.find_one(
            {"_id": ObjectId(admin["organization_id"])}
        )
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Create JWT token
        token_data = {
            "admin_id": str(admin["_id"]),
            "organization_id": str(organization["_id"]),
            "email": admin["email"]
        }
        
        access_token = jwt_handler.create_access_token(token_data)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            admin_id=str(admin["_id"]),
            organization_name=organization["organization_name"],
            email=admin["email"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )