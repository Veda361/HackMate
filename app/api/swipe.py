from fastapi import APIRouter, Depends, Header, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.swipe import Swipe
from app.models.match import Match
from app.core.firebase import verify_token

# ✅ SAFE IMPORT (NO CRASH)
try:
    from app.api.chat import manager
except:
    manager = None

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
async def swipe_user(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        swiper_uid = decoded["uid"]
        swiped_uid = data.get("swiped_uid")
        liked = data.get("liked")

        if swiper_uid == swiped_uid:
            return {"error": "Cannot swipe yourself"}

        # 🔥 UPSERT SWIPE
        existing = db.query(Swipe).filter(
            Swipe.swiper_uid == swiper_uid,
            Swipe.swiped_uid == swiped_uid
        ).first()

        if existing:
            existing.liked = liked
        else:
            db.add(Swipe(
                swiper_uid=swiper_uid,
                swiped_uid=swiped_uid,
                liked=liked
            ))

        db.commit()

        # 🔥 CHECK MUTUAL LIKE
        if liked:
            reverse = db.query(Swipe).filter(
                Swipe.swiper_uid == swiped_uid,
                Swipe.swiped_uid == swiper_uid,
                Swipe.liked == True
            ).first()

            if reverse:
                already = db.query(Match).filter(
                    ((Match.user1_uid == swiper_uid) & (Match.user2_uid == swiped_uid)) |
                    ((Match.user1_uid == swiped_uid) & (Match.user2_uid == swiper_uid))
                ).first()

                if not already:
                    db.add(Match(
                        user1_uid=swiper_uid,
                        user2_uid=swiped_uid
                    ))
                    db.commit()

                    # 🔥 REAL-TIME MATCH (SAFE)
                    if manager:
                        try:
                            await manager.send_personal_message({
                                "type": "match",
                                "user": swiped_uid
                            }, swiper_uid)

                            await manager.send_personal_message({
                                "type": "match",
                                "user": swiper_uid
                            }, swiped_uid)

                        except Exception as e:
                            print("⚠️ WS ERROR:", e)

                return {"msg": "It's a MATCH 🎉"}

        return {"msg": "Swipe stored"}

    except Exception as e:
        print("❌ SWIPE ERROR:", e)
        return {"error": str(e)}