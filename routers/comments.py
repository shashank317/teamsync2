from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models, schemas
from typing import List

router = APIRouter()

# ✅ Add a comment to a task
@router.post("/tasks/{task_id}/comments", response_model=schemas.CommentOut)
def add_comment_to_task(
    task_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    task = db.query(models.Task).join(models.Project).filter(
        models.Task.id == task_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found or unauthorized")

    new_comment = models.Comment(
        content=comment.content,
        task_id=task_id,
        user_id=current_user.id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return schemas.CommentOut(
        id=new_comment.id,
        content=new_comment.content,
        timestamp=new_comment.timestamp,
        user_name=current_user.name  # 👈 set commenter name in response
    )

# ✅ Get all comments for a task
@router.get("/tasks/{task_id}/comments", response_model=List[schemas.CommentOut])
def get_comments_for_task(
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

    comments = db.query(models.Comment).join(models.User).filter(
        models.Comment.task_id == task_id
    ).order_by(models.Comment.timestamp.asc()).all()

    return [
        schemas.CommentOut(
            id=c.id,
            content=c.content,
            timestamp=c.timestamp,
            user_name=c.user.name
        )
        for c in comments
    ]
