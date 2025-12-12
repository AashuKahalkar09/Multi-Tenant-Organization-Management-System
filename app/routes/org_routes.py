from fastapi import APIRouter, HTTPException, status, Depends
from app.models.schemas import (
    OrganizationCreate, OrganizationGet, OrganizationUpdate,
    OrganizationDelete, OrganizationResponse, MessageResponse
)
from app.db import db_manager
from app.auth.hashing import password_hasher
from app.auth.dependencies import get_current_admin
from bson import ObjectId
from datetime import datetime
import re
from typing import Dict

router = APIRouter(prefix="/org", tags=["Organizations"])

def create_slug(name: str) -> str:
    """Create a URL-friendly slug from organization name"""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '_', slug)
    return f"org_{slug}"

@router.post("/create", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(org_data: OrganizationCreate):
    """
    Create a new organization with admin user
    
    - Creates organization record
    - Creates admin user with hashed password
    - Creates dedicated MongoDB collection for organization
    """
    try:
        master_db = db_manager.get_master_db()
        
        # Check if organization already exists
        existing_org = master_db.organizations.find_one(
            {"organization_name": org_data.organization_name}
        )
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization '{org_data.organization_name}' already exists"
            )
        
        # Check if admin email already exists
        existing_admin = master_db.admins.find_one({"email": org_data.email})
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Admin with email '{org_data.email}' already exists"
            )
        
        # Create collection name
        collection_name = create_slug(org_data.organization_name)
        
        # Hash password
        password_hash = password_hasher.hash_password(org_data.password)
        
        # Create organization document
        org_doc = {
            "organization_name": org_data.organization_name,
            "collection_name": collection_name,
            "admin_user_id": None,  # Will update after creating admin
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        org_result = master_db.organizations.insert_one(org_doc)
        org_id = str(org_result.inserted_id)
        
        # Create admin document
        admin_doc = {
            "email": org_data.email,
            "password_hash": password_hash,
            "organization_id": org_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        admin_result = master_db.admins.insert_one(admin_doc)
        admin_id = str(admin_result.inserted_id)
        
        # Update organization with admin_user_id
        master_db.organizations.update_one(
            {"_id": ObjectId(org_id)},
            {"$set": {"admin_user_id": admin_id}}
        )
        
        # Create organization collection
        db_manager.create_org_collection(collection_name)
        
        return OrganizationResponse(
            id=org_id,
            organization_name=org_data.organization_name,
            collection_name=collection_name,
            admin_email=org_data.email,
            created_at=org_doc["created_at"].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}"
        )

@router.post("/get", response_model=OrganizationResponse)
async def get_organization(org_data: OrganizationGet):
    """
    Get organization details by name
    """
    try:
        master_db = db_manager.get_master_db()
        
        # Find organization
        org = master_db.organizations.find_one(
            {"organization_name": org_data.organization_name}
        )
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization '{org_data.organization_name}' not found"
            )
        
        # Get admin details
        admin = master_db.admins.find_one({"_id": ObjectId(org["admin_user_id"])})
        
        return OrganizationResponse(
            id=str(org["_id"]),
            organization_name=org["organization_name"],
            collection_name=org["collection_name"],
            admin_email=admin["email"] if admin else "N/A",
            created_at=org["created_at"].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organization: {str(e)}"
        )

@router.put("/update", response_model=MessageResponse)
async def update_organization(
    org_data: OrganizationUpdate,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    Update organization details (requires authentication)
    
    - Can update organization name (creates new collection and migrates data)
    - Can update admin email and password
    """
    try:
        master_db = db_manager.get_master_db()
        
        # Verify admin has permission to update this organization
        if current_admin["organization_name"] != org_data.old_organization_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this organization"
            )
        
        org_id = current_admin["organization_id"]
        org = master_db.organizations.find_one({"_id": ObjectId(org_id)})
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        update_data = {"updated_at": datetime.utcnow()}
        
        # Check if organization name is being changed
        if org_data.new_organization_name != org_data.old_organization_name:
            # Check if new name already exists
            existing_org = master_db.organizations.find_one(
                {"organization_name": org_data.new_organization_name}
            )
            if existing_org:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Organization '{org_data.new_organization_name}' already exists"
                )
            
            # Create new collection
            new_collection_name = create_slug(org_data.new_organization_name)
            old_collection_name = org["collection_name"]
            
            # Copy data from old collection to new
            old_collection = db_manager.get_org_collection(old_collection_name)
            new_collection = db_manager.create_org_collection(new_collection_name)
            
            # Migrate all documents
            documents = list(old_collection.find())
            if documents:
                new_collection.insert_many(documents)
            
            # Drop old collection
            db_manager.drop_org_collection(old_collection_name)
            
            update_data["organization_name"] = org_data.new_organization_name
            update_data["collection_name"] = new_collection_name
        
        # Update organization
        master_db.organizations.update_one(
            {"_id": ObjectId(org_id)},
            {"$set": update_data}
        )
        
        # Update admin if email or password provided
        admin_update = {"updated_at": datetime.utcnow()}
        
        if org_data.email:
            # Check if email already exists for another admin
            existing_admin = master_db.admins.find_one({
                "email": org_data.email,
                "_id": {"$ne": ObjectId(current_admin["admin_id"])}
            })
            if existing_admin:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use by another admin"
                )
            admin_update["email"] = org_data.email
        
        if org_data.password:
            admin_update["password_hash"] = password_hasher.hash_password(org_data.password)
        
        if len(admin_update) > 1:  # More than just updated_at
            master_db.admins.update_one(
                {"_id": ObjectId(current_admin["admin_id"])},
                {"$set": admin_update}
            )
        
        return MessageResponse(
            message="Organization updated successfully",
            details={
                "organization_name": org_data.new_organization_name,
                "email_updated": org_data.email is not None,
                "password_updated": org_data.password is not None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )

@router.delete("/delete", response_model=MessageResponse)
async def delete_organization(
    org_data: OrganizationDelete,
    current_admin: Dict = Depends(get_current_admin)
):
    """
    Delete organization (requires authentication)
    
    - Deletes organization collection
    - Deletes organization record
    - Deletes admin user
    """
    try:
        master_db = db_manager.get_master_db()
        
        # Verify admin has permission to delete this organization
        if current_admin["organization_name"] != org_data.organization_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this organization"
            )
        
        org_id = current_admin["organization_id"]
        collection_name = current_admin["collection_name"]
        
        # Drop organization collection
        db_manager.drop_org_collection(collection_name)
        
        # Delete admin user
        master_db.admins.delete_one({"_id": ObjectId(current_admin["admin_id"])})
        
        # Delete organization
        master_db.organizations.delete_one({"_id": ObjectId(org_id)})
        
        return MessageResponse(
            message="Organization deleted successfully",
            details={
                "organization_name": org_data.organization_name,
                "collection_deleted": collection_name
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete organization: {str(e)}"
        )