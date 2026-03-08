from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base
from sqlalchemy import Column, Integer, String
from database import Base # Импортируем ОДИН раз отсюда

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True)
    username = Column(String)
    status = Column(String, default="pending")
    # ... остальные поля
    

# Таблица для пользователей (регистрация + опрос + статус)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False) # ID телеграма
    username = Column(String, nullable=True)             # Юзернейм
    
    # Статус: pending (ожидает), approved (одобрен), banned (отклонен)
    status = Column(String, default="pending") 
    
    # Данные опроса
    source = Column(String, nullable=True)          # Источник
    source_detail = Column(String, nullable=True)   # Детали источника
    teams = Column(String, nullable=True)           # Опыт в тимах
    reason = Column(String, nullable=True)          # Почему вступить к нам
    
    # Статистика
    archives = Column(Integer, default=0)           # Сколько архивов сдал
    payouts = Column(Integer, default=0)            # Сумма выплат
    
    timestamp = Column(DateTime, default=datetime.utcnow)

# Таблица для фотографий (дедупликация)
class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True)
    crc32_hash = Column(String, index=True, nullable=False) # Индекс для быстрого поиска
    file_name = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)