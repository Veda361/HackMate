from fastapi import APIRouter, Depends, Header, Body
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.swipe import Swipe
from app.models.match import Match
from app.core.firebase import verify_token

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

        print("🔥 SWIPE")
        print(swiper_uid, "->", swiped_uid)

        if not swiped_uid:
            return {"error": "Missing swiped_uid"}

        if swiper_uid == swiped_uid:
            return {"error": "Cannot swipe yourself"}

        # =========================
        # ALREADY SWIPED
        # =========================
        existing = db.query(Swipe).filter(
            Swipe.swiper_uid == swiper_uid,
            Swipe.swiped_uid == swiped_uid
        ).first()

        if existing:
            return {
                "msg": "Already swiped",
                "match": False
            }

        # =========================
        # SAVE SWIPE
        # =========================
        swipe = Swipe(
            swiper_uid=swiper_uid,
            swiped_uid=swiped_uid,
            liked=liked
        )

        db.add(swipe)
        db.commit()

        print("✅ Swipe stored")

        # =========================
        # CHECK MUTUAL MATCH
        # =========================
        if liked:

            reverse = db.query(Swipe).filter(
                Swipe.swiper_uid == swiped_uid,
                Swipe.swiped_uid == swiper_uid,
                Swipe.liked == True
            ).first()

            if reverse:

                print("🔥 MATCH FOUND")

                already = db.query(Match).filter(
                    (
                        (Match.user1_uid == swiper_uid) &
                        (Match.user2_uid == swiped_uid)
                    ) |
                    (
                        (Match.user1_uid == swiped_uid) &
                        (Match.user2_uid == swiper_uid)
                    )
                ).first()

                if not already:

                    match = Match(
                        user1_uid=swiper_uid,
                        user2_uid=swiped_uid,
                        chat_enabled=True
                    )

                    db.add(match)
                    db.commit()

                    print("✅ MATCH CREATED")

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
                            print("❌ WS ERROR:", e)

                return {
                    "msg": "MATCH CREATED",
                    "match": True
                }

        return {
            "msg": "Swipe stored",
            "match": False
        }

    except Exception as e:
        print("❌ SWIPE ERROR:", e)
        return {"error": str(e)}