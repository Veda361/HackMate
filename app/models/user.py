from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    firebase_uid = Column(String, unique=True)
    email = Column(String)
    skills = Column(String)
    username = Column(String)
    avatar = Column(String, nullable=True)