from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    user1_uid = Column(String)
    user2_uid = Column(String)