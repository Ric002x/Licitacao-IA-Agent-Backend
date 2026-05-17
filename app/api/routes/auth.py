from datetime import timedelta, datetime
from app.schemas.auth import AuthBody, Token
from app.schemas.user import UserRead
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, SessionDep
from app.models.models import User
from app.core.config import settings
from jose import jwt


router = APIRouter(tags=["auth"], prefix="/auth")


def create_token(user_id):
    now = datetime.now()
    expiration_time = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_in = now + expiration_time
    exp = expires_in.timestamp()

    to_encode = {"user_id": str(user_id), "exp": exp}
    token = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)
    return token


def authenticate_user(session, email, password):
    user = session.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="user not find for that email"
        )

    if user.verify_password(password):
        token_jwt = create_token(user.id)
        return JSONResponse(
            {
                "access_token": token_jwt,
                "token_type": "Bearer"
            }
        )
    else:
        raise HTTPException(
            status_code=401,
            detail="invalid credentials"
        )


@router.post("/private_auth", include_in_schema=False)
def private_auth_login_for_docs(
    session: SessionDep, username: str = Form(None), password: str = Form(None)
):
    return authenticate_user(session, username, password)


@router.post("/login", response_model=Token)
def user_login(session: SessionDep, data: AuthBody):
    return authenticate_user(session, data.email, data.password)


@router.post("/", response_model=UserRead)
def get_current_user(current_user: CurrentUser):
    return current_user
