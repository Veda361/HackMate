from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__ = "hackmate_users"  # 🔥 CHANGE THIS

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True)
    email = Column(String)
    username = Column(String)
    skills = Column(String)
    avatar = Column(String)