from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import User

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def init_db(session: Session) -> None:

    user = session.query(User).filter(
        User.username == settings.FIRST_SUPERUSER_USERNAME).first()

    if not user:
        user_in = User(
            email=settings.FIRST_SUPERUSER,
            username=settings.FIRST_SUPERUSER_USERNAME,
            is_superuser=True
        )
        user_in.set_password(settings.FIRST_SUPERUSER_PASSWORD)

        session.add(user_in)
        session.commit()
        session.refresh(user_in)
