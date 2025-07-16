from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime

# -------------------------------
# ✅ User Schemas
# -------------------------------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# -------------------------------
# ✅ Project Schemas
# -------------------------------
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ProjectOut(BaseModel):
    id: int
    title: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)

# -------------------------------
# ✅ File Attachment Schema
# -------------------------------
class AttachmentOut(BaseModel):
    id: int
    filename: str
    filepath: str

    model_config = ConfigDict(from_attributes=True)

# -------------------------------
# ✅ Comment Schemas
# -------------------------------
class CommentCreate(BaseModel):
    content: str

class CommentOut(BaseModel):
    id: int
    content: str
    timestamp: datetime
    user_name: str  # 👈 For displaying user who commented

    model_config = ConfigDict(from_attributes=True)

# -------------------------------
# ✅ Task Schemas
# -------------------------------
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    due_date: Optional[datetime]
    attachments: List[AttachmentOut] = []
    comments: List[CommentOut] = []  # ✅ Include comments with user_name

    model_config = ConfigDict(from_attributes=True)

class PasswordReset(BaseModel):
    email: EmailStr
    new_password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
