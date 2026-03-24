from fastapi import APIRouter, Depends, Header, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.swipe import Swipe
from app.models.match import Match
from app.core.firebase import verify_token

# 🔥 IMPORT YOUR WS MANAGER
from app.api.chat import manager  

router = APIRouter()


# ✅ DB Dependency
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
        # 🔐 Verify user
        token = authorization.split(" ")[1]
        decoded = verify_token(token)

        swiper_uid = decoded["uid"]
        swiped_uid = data.get("swiped_uid")
        liked = data.get("liked")

        # ❌ Prevent self swipe
        if swiper_uid == swiped_uid:
            return {"error": "Cannot swipe yourself"}

        # 🔥 CHECK IF SWIPE ALREADY EXISTS
        existing_swipe = db.query(Swipe).filter(
            Swipe.swiper_uid == swiper_uid,
            Swipe.swiped_uid == swiped_uid
        ).first()

        if existing_swipe:
            existing_swipe.liked = liked
        else:
            swipe = Swipe(
                swiper_uid=swiper_uid,
                swiped_uid=swiped_uid,
                liked=liked
            )
            db.add(swipe)

        db.commit()

        # 🔥 CHECK MUTUAL LIKE
        if liked:
            reverse_swipe = db.query(Swipe).filter(
                Swipe.swiper_uid == swiped_uid,
                Swipe.swiped_uid == swiper_uid,
                Swipe.liked == True
            ).first()

            if reverse_swipe:
                # ✅ CHECK IF MATCH ALREADY EXISTS
                already_match = db.query(Match).filter(
                    ((Match.user1_uid == swiper_uid) & (Match.user2_uid == swiped_uid)) |
                    ((Match.user1_uid == swiped_uid) & (Match.user2_uid == swiper_uid))
                ).first()

                if not already_match:
                    match = Match(
                        user1_uid=swiper_uid,
                        user2_uid=swiped_uid
                    )
                    db.add(match)
                    db.commit()

                    # 🔥 REAL-TIME MATCH EVENT
                    try:
                        await manager.send_personal_message({
                            "type": "match",
                            "user": swiped_uid
                        }, swiper_uid)

                        await manager.send_personal_message({
                            "type": "match",
                            "user": swiper_uid
                        }, swiped_uid)

                    except Exception as ws_error:
                        print("⚠️ WS SEND ERROR:", ws_error)

                return {"msg": "It's a MATCH 🎉"}

        return {"msg": "Swipe stored"}

    except Exception as e:
        print("❌ SWIPE ERROR:", e)
        return {"error": str(e)}