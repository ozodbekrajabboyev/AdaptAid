from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import (
    clear_session_cookie,
    create_token,
    hash_password,
    set_session_cookie,
    verify_password,
)
from app.models import User
from app.models.base import Role
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services import classes as classes_service
from engine import clock

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)) -> User:
    if body.role == "teacher" and body.invite_code != get_settings().teacher_invite_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The teacher invite code is not correct.")
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Sign in instead.")
    now = clock.now()
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=Role(body.role),
        created_at=now,
        last_active_at=now,
    )
    db.add(user)
    db.flush()
    if body.join_code and user.role == Role.student:
        classes_service.join_class(db, user, body.join_code)
    db.commit()
    set_session_cookie(response, create_token(user.id, user.role.value))
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is not correct.")
    user.last_active_at = clock.now()
    db.commit()
    set_session_cookie(response, create_token(user.id, user.role.value))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
