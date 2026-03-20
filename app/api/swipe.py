from fastapi import APIRouter, Depends, Header, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.swipe import Swipe
from app.models.match import Match
from app.core.firebase import verify_token

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def swipe_user(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    decoded = verify_token(token)

    swiper_uid = decoded["uid"]
    swiped_uid = data.get("swiped_uid")
    liked = data.get("liked")

    # 🔥 Store swipe
    swipe = Swipe(
        swiper_uid=swiper_uid,
        swiped_uid=swiped_uid,
        liked=liked
    )
    db.add(swipe)
    db.commit()

    # 🔥 Check mutual like
    if liked:
        existing = db.query(Swipe).filter(
            Swipe.swiper_uid == swiped_uid,
            Swipe.swiped_uid == swiper_uid,
            Swipe.liked == True
        ).first()

        if existing:
            match = Match(
                user1_uid=swiper_uid,
                user2_uid=swiped_uid
            )
            db.add(match)
            db.commit()

            return {"msg": "It's a MATCH 🎉"}

    return {"msg": "Swipe stored"}