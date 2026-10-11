
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker 
from src.config.settings import settings



database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

SessionFactory = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)