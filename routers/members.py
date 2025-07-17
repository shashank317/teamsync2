from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Project, ProjectMember, User
from auth import get_current_user
from pydantic import BaseModel
from auth import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from datetime import datetime, timedelta

INVITE_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day


router = APIRouter(
    prefix="/projects",
    tags=["Project Members"]
)

# 📦 Pydantic Schemas
class MemberAddRequest(BaseModel):
    user_id: int
    role: str

class MemberUpdateRequest(BaseModel):
    role: str

class MemberResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

# ➕ Add Member to Project
@router.post("/{project_id}/members", response_model=MemberResponse)
def add_member(project_id: int, data: MemberAddRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=403, detail="You do not own this project")

    existing = db.query(ProjectMember).filter_by(project_id=project_id, user_id=data.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member of this project")

    user = db.query(User).filter_by(id=data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    member = ProjectMember(user_id=data.user_id, project_id=project_id, role=data.role)
    db.add(member)
    db.commit()
    db.refresh(member)

    return MemberResponse(user_id=user.id, name=user.name, email=user.email, role=member.role)

# 📃 Get All Members of a Project
@router.get("/{project_id}/members", response_model=List[MemberResponse])
def get_members(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    members = (
        db.query(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )

    return [MemberResponse(user_id=u.id, name=u.name, email=u.email, role=m.role) for m, u in members]

# 🔁 Update Member Role
@router.put("/{project_id}/members/{user_id}", response_model=MemberResponse)
def update_member_role(project_id: int, user_id: int, data: MemberUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=403, detail="You do not own this project")

    member = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.role = data.role
    db.commit()

    user = db.query(User).filter_by(id=user_id).first()
    return MemberResponse(user_id=user.id, name=user.name, email=user.email, role=member.role)

# ❌ Remove Member
@router.delete("/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=403, detail="You do not own this project")

    member = db.query(ProjectMember).filter_by(project_id=project_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
    return {"message": "Member removed"}

@router.get("/{project_id}/invite-link")
def generate_invite_link(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=403, detail="You do not own this project")

    expire = datetime.utcnow() + timedelta(minutes=INVITE_TOKEN_EXPIRE_MINUTES)
    payload = {
        "project_id": project_id,
        "exp": expire
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    link = f"http://localhost:8000/projects/join?token={token}"
    return {"invite_link": link}

@router.post("/join")
def join_project_via_token(token: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        project_id = payload.get("project_id")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired invite token")

    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already a member
    existing = db.query(ProjectMember).filter_by(project_id=project_id, user_id=current_user.id).first()
    if existing:
        return {"message": "Already a member of this project"}

    # Add user as a "member"
    member = ProjectMember(user_id=current_user.id, project_id=project_id, role="member")
    db.add(member)
    db.commit()

    return {"message": f"You have joined the project '{project.title}' successfully!"}
