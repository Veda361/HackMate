from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class Swipe(Base):
    __tablename__ = "hackmate_swipes"

    id = Column(Integer, primary_key=True, index=True)
    swiper_uid = Column(String, index=True)
    swiped_uid = Column(String, index=True)
    liked = Column(Boolean, default=False)