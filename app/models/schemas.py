from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Request Models
class OrganizationCreate(BaseModel):
    organization_name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class OrganizationGet(BaseModel):
    organization_name: str

class OrganizationUpdate(BaseModel):
    old_organization_name: str
    new_organization_name: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)

class OrganizationDelete(BaseModel):
    organization_name: str

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

# Response Models
class OrganizationResponse(BaseModel):
    id: str
    organization_name: str
    collection_name: str
    admin_email: str
    created_at: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str
    organization_name: str
    email: str

class MessageResponse(BaseModel):
    message: str
    details: Optional[dict] = None

# Database Models (for internal use)
class OrganizationDB(BaseModel):
    organization_name: str
    collection_name: str
    admin_user_id: str
    created_at: datetime
    updated_at: datetime

class AdminDB(BaseModel):
    email: str
    password_hash: str
    organization_id: str
    created_at: datetime
    updated_at: datetime