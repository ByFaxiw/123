from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True)

    crc32_hash = Column(String, index=True)

    file_name = Column(String)

    user_id = Column(Integer)

    timestamp = Column(DateTime, default=datetime.utcnow)