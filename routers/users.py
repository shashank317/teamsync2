from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas, utils
from auth import create_access_token, get_current_user
from database import get_db

router = APIRouter()

@router.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ Password validation rules
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.islower() for c in user.password):
        raise HTTPException(status_code=400, detail="Password must include a lowercase letter")
    if not any(c.isupper() for c in user.password):
        raise HTTPException(status_code=400, detail="Password must include an uppercase letter")
    if not any(c.isdigit() for c in user.password):
        raise HTTPException(status_code=400, detail="Password must include a number")
    if not any(c in "!@#$%^&*()-_+=" for c in user.password):
        raise HTTPException(status_code=400, detail="Password must include a special character (!@#$...)")

    hashed_password = utils.hash_password(user.password)
    new_user = models.User(name=user.name, email=user.email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ✅ Auto-login after signup
    token = create_access_token(data={"user_id": new_user.id})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not utils.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"user_id": db_user.id})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.name
    }

@router.post("/reset-password")
def reset_password(
    data: schemas.PasswordReset,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Password rules
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.islower() for c in data.new_password):
        raise HTTPException(status_code=400, detail="Password must include a lowercase letter")
    if not any(c.isupper() for c in data.new_password):
        raise HTTPException(status_code=400, detail="Password must include an uppercase letter")
    if not any(c.isdigit() for c in data.new_password):
        raise HTTPException(status_code=400, detail="Password must include a number")
    if not any(c in "!@#$%^&*()-_+=" for c in data.new_password):
        raise HTTPException(status_code=400, detail="Password must include a special character (!@#$...)")

    user.password = utils.hash_password(data.new_password)
    db.commit()

    return {"message": "Password reset successfully"}


@router.put("/me/update")
def update_profile(
    updates: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if updates.name:
        current_user.name = updates.name

    if updates.email:
        # Check for conflict
        if db.query(models.User).filter(models.User.email == updates.email, models.User.id != current_user.id).first():
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = updates.email

    if updates.new_password:
        if not updates.current_password or not utils.verify_password(updates.current_password, current_user.password):
            raise HTTPException(status_code=403, detail="Current password is incorrect")
        current_user.password = utils.hash_password(updates.new_password)

    db.commit()
    return {"message": "Profile updated successfully"}
