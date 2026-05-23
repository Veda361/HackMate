from fastapi import APIRouter, Depends, Header, Body
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.match import Match
from app.models.user import User
from app.models.swipe import Swipe
from app.core.firebase import verify_token

# 🔥 SAFE IMPORT
try:
    from app.api.chat import manager
except:
    manager = None

router = APIRouter()


# =========================
# DB
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# GET MATCHES
# =========================
@router.get("/")
def get_my_matches(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        uid = verify_token(
            authorization.split(" ")[1]
        )["uid"]

        results = []

        # =========================
        # MATCHES
        # =========================
        matches = db.query(Match).filter(
            (Match.user1_uid == uid) |
            (Match.user2_uid == uid)
        ).all()

        for m in matches:

            other_uid = (
                m.user2_uid
                if m.user1_uid == uid
                else m.user1_uid
            )

            user = db.query(User).filter(
                User.firebase_uid == other_uid
            ).first()

            if user:
                results.append({
                    "uid": user.firebase_uid,
                    "username": user.username,
                    "email": user.email,
                    "skills": user.skills,
                    "type": "match",
                    "chat_enabled": m.chat_enabled
                })

        # =========================
        # INCOMING REQUESTS
        # =========================
        incoming = db.query(Swipe).filter(
            Swipe.swiped_uid == uid,
            Swipe.liked == True
        ).all()

        for s in incoming:

            already = db.query(Match).filter(
                (
                    (Match.user1_uid == s.swiper_uid) &
                    (Match.user2_uid == uid)
                ) |
                (
                    (Match.user1_uid == uid) &
                    (Match.user2_uid == s.swiper_uid)
                )
            ).first()

            if already:
                continue

            user = db.query(User).filter(
                User.firebase_uid == s.swiper_uid
            ).first()

            if user:
                results.append({
                    "uid": user.firebase_uid,
                    "username": user.username,
                    "email": user.email,
                    "skills": user.skills,
                    "type": "request",
                    "chat_enabled": False
                })

        # =========================
        # SENT REQUESTS
        # =========================
        sent = db.query(Swipe).filter(
            Swipe.swiper_uid == uid,
            Swipe.liked == True
        ).all()

        for s in sent:

            already = db.query(Match).filter(
                (
                    (Match.user1_uid == uid) &
                    (Match.user2_uid == s.swiped_uid)
                ) |
                (
                    (Match.user1_uid == s.swiped_uid) &
                    (Match.user2_uid == uid)
                )
            ).first()

            if already:
                continue

            user = db.query(User).filter(
                User.firebase_uid == s.swiped_uid
            ).first()

            if user:
                results.append({
                    "uid": user.firebase_uid,
                    "username": user.username,
                    "email": user.email,
                    "skills": user.skills,
                    "type": "sent",
                    "chat_enabled": False
                })

        print("✅ MATCH RESULTS:", results)

        return results

    except Exception as e:
        print("❌ MATCH ERROR:", e)
        return []


# =========================
# ACCEPT REQUEST
# =========================
@router.post("/accept")
async def accept_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        uid = verify_token(
            authorization.split(" ")[1]
        )["uid"]

        other_uid = data.get("uid")

        existing = db.query(Match).filter(
            (
                (Match.user1_uid == uid) &
                (Match.user2_uid == other_uid)
            ) |
            (
                (Match.user1_uid == other_uid) &
                (Match.user2_uid == uid)
            )
        ).first()

        # =========================
        # MATCH EXISTS
        # =========================
        if existing:

            existing.chat_enabled = True
            db.commit()

            print("✅ CHAT ENABLED")

            if manager:
                try:
                    await manager.send_personal_message(
                        {
                            "type": "invite_accepted",
                            "user": uid
                        },
                        other_uid
                    )

                except Exception as e:
                    print("❌ WS ERROR:", e)

            return {"msg": "Chat enabled ✅"}

        # =========================
        # CREATE NEW MATCH
        # =========================
        match = Match(
            user1_uid=uid,
            user2_uid=other_uid,
            chat_enabled=True
        )

        db.add(match)
        db.commit()

        # =========================
        # DELETE REQUEST SWIPE
        # =========================
        db.query(Swipe).filter(
            Swipe.swiper_uid == other_uid,
            Swipe.swiped_uid == uid
        ).delete()

        db.commit()

        print("🔥 NEW MATCH CREATED")

        # =========================
        # REALTIME
        # =========================
        if manager:
            try:
                await manager.send_personal_message(
                    {
                        "type": "invite_accepted",
                        "user": uid
                    },
                    other_uid
                )

                await manager.send_personal_message(
                    {
                        "type": "invite_accepted",
                        "user": other_uid
                    },
                    uid
                )

            except Exception as e:
                print("❌ WS ERROR:", e)

        return {"msg": "Accepted ✅"}

    except Exception as e:
        print("❌ ACCEPT ERROR:", e)
        return {"error": str(e)}


# =========================
# REJECT REQUEST
# =========================
@router.post("/reject")
def reject_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        uid = verify_token(
            authorization.split(" ")[1]
        )["uid"]

        other_uid = data.get("uid")

        db.query(Swipe).filter(
            Swipe.swiper_uid == other_uid,
            Swipe.swiped_uid == uid
        ).delete()

        db.commit()

        print("❌ REQUEST REJECTED")

        return {"msg": "Rejected ❌"}

    except Exception as e:
        print("❌ REJECT ERROR:", e)
        return {"error": str(e)}