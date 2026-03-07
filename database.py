from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import DB_URL

engine = create_async_engine(DB_URL)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()