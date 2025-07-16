from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models, schemas
from typing import List
from datetime import datetime
import os
import shutil
from fastapi.responses import FileResponse

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------
# ✅ Project Endpoints
# -------------------------------

@router.post("/projects/create", response_model=schemas.ProjectOut)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_project = models.Project(
        title=project.title,
        description=project.description,
        owner_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@router.get("/projects", response_model=List[schemas.ProjectOut])
def get_user_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Project).filter(models.Project.owner_id == current_user.id).all()

# -------------------------------
# ✅ Create Task with File Upload
# -------------------------------

@router.post("/projects/{project_id}/tasks", response_model=schemas.TaskOut)
def create_task_for_project(
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("pending"),
    due_date: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")

    due = datetime.fromisoformat(due_date) if due_date else None

    new_task = models.Task(
        title=title,
        description=description,
        status=status,
        due_date=due,
        project_id=project_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    if file:
        filepath = os.path.join(UPLOAD_DIR, file.filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        attachment = models.FileAttachment(
            filename=file.filename,
            filepath=filepath,
            task_id=new_task.id
        )
        db.add(attachment)
        db.commit()

    db.refresh(new_task)
    return new_task

# -------------------------------
# ✅ Get All Tasks (with Comments + Attachments)
# -------------------------------

@router.get("/projects/{project_id}/tasks", response_model=List[schemas.TaskOut])
def get_tasks_for_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")

    tasks = db.query(models.Task).filter(models.Task.project_id == project_id).all()

    return [
        schemas.TaskOut(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            due_date=t.due_date,
            attachments=[
                schemas.AttachmentOut(
                    id=a.id,
                    filename=a.filename,
                    filepath=a.filepath
                ) for a in t.attachments
            ],
            comments=[
                schemas.CommentOut(
                    id=c.id,
                    content=c.content,
                    timestamp=c.timestamp,
                    user_name=c.user.name
                ) for c in t.comments
            ]
        )
        for t in tasks
    ]

# -------------------------------
# ✅ Task Edit / Delete
# -------------------------------

@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized")

    if task_update.title is not None:
        task.title = task_update.title
    if task_update.description is not None:
        task.description = task_update.description
    if task_update.status is not None:
        task.status = task_update.status
    if task_update.due_date is not None:
        task.due_date = task_update.due_date

    db.commit()
    db.refresh(task)
    return task

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized")

    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted successfully"}

# -------------------------------
# ✅ Analytics
# -------------------------------

@router.get("/projects/{project_id}/analytics")
def get_project_analytics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")

    tasks = db.query(models.Task).filter(models.Task.project_id == project_id).all()

    total_tasks = len(tasks)
    pending = sum(1 for t in tasks if t.status == "pending")
    in_progress = sum(1 for t in tasks if t.status == "in-progress")
    done = sum(1 for t in tasks if t.status == "done")

    now = datetime.utcnow()
    overdue = sum(1 for t in tasks if t.due_date and t.due_date < now and t.status != "done")

    return {
        "total": total_tasks,
        "pending": pending,
        "in_progress": in_progress,
        "done": done,
        "overdue": overdue
    }
