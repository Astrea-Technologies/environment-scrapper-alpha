from sqlmodel import Session, create_engine, select, SQLModel

# Updated import to match new architecture
from app.services import user as user_service
from app.core.config import settings
# Updated model imports
from app.db.models.user import User
from app.schemas.user import UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # This line was previously commented, but we need it for the models to work
    
    # This works because the models are already imported and registered from app.models
    SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        # Fixed parameter name to match the service function signature
        user = user_service.create_user(session=session, user_create=user_in)
