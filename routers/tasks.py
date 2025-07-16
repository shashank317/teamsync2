from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models, schemas
from typing import List
from fastapi import UploadFile, File
import os
from uuid import uuid4

router = APIRouter()

# ✅ Create Task for a Project
@router.post("/projects/{project_id}/tasks", response_model=schemas.TaskOut)
def create_task(
    project_id: int,
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_task = models.Task(
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        project_id=project_id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


# ✅ Get Tasks for a Project
@router.get("/projects/{project_id}/tasks", response_model=List[schemas.TaskOut])
def get_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
                    user_name=c.user.name if c.user else "Unknown"  # 👈 handle missing user
                ) for c in t.comments
            ]
        )
        for t in tasks
    ]


# ✅ Update a Task
@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    updated_task: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.query(models.Project).filter(
        models.Project.id == task.project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")

    if updated_task.title is not None:
        task.title = updated_task.title
    if updated_task.description is not None:
        task.description = updated_task.description
    if updated_task.status is not None:
        task.status = updated_task.status
    if updated_task.due_date is not None:
        task.due_date = updated_task.due_date

    db.commit()
    db.refresh(task)
    return task


# ✅ Delete a Task
@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = db.query(models.Project).filter(
        models.Project.id == task.project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}

UPLOAD_DIR = "uploads"

@router.post("/tasks/{task_id}/upload", response_model=schemas.AttachmentOut)
def upload_file(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized")

    filename = f"{uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(file.file.read())

    attachment = models.FileAttachment(
        filename=file.filename,
        filepath=filepath,
        task_id=task_id
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/tasks/{task_id}/attachments", response_model=List[schemas.AttachmentOut])
def get_attachments(
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

    return task.attachments