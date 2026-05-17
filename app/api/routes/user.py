from app.schemas.user import UserCreate, UserUpdate
from fastapi import APIRouter, HTTPException, status
from app.models.models import User
from app.api.deps import SessionDep, CurrentUser

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("/criar", status_code=201)
def criar_usuario(data: UserCreate, db: SessionDep):
    existing_user = db.query(User).filter(
        User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user_obj = User(
        email=data.email,
        username=data.username,
    )

    user_obj.set_password(data.password)
    db.add(user_obj)
    db.commit()

    return user_obj.data


@router.put("/atualizar")
def update_user(
        current_user: CurrentUser, session: SessionDep, data: UserUpdate):
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "password":
            current_user.set_password(value)
        else:
            setattr(current_user, key, value)

    session.commit()
    session.refresh(current_user)
    return current_user
