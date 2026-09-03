from database import Base
from sqlalchemy import Column, Float, Integer, String


class User(Base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  telegram_id = Column(Integer, unique=True, index=True)
  wallet_address = Column(String, nullable=True)
  balance = Column(Float, default=0.0)


class Task(Base):
  __tablename__ = "tasks"

  id = Column(Integer, primary_key=True, index=True)
  title = Column(String, index=True)
  description = Column(String)
  reward = Column(Float, default=0.0)
  is_active = Column(Integer, default=1)

