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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 GET MATCHES
@router.get("/")
def get_my_matches(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        uid = verify_token(authorization.split(" ")[1])["uid"]

        results = []

        # 🔥 MATCHES
        matches = db.query(Match).filter(
            (Match.user1_uid == uid) | (Match.user2_uid == uid)
        ).all()

        for m in matches:
            other_uid = m.user2_uid if m.user1_uid == uid else m.user1_uid

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
                    "chat_enabled": True
                })

        # 🔥 INCOMING
        incoming = db.query(Swipe).filter(
            Swipe.swiped_uid == uid,
            Swipe.liked == True
        ).all()

        for s in incoming:
            already = db.query(Match).filter(
                ((Match.user1_uid == s.swiper_uid) & (Match.user2_uid == uid)) |
                ((Match.user1_uid == uid) & (Match.user2_uid == s.swiper_uid))
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

        # 🔥 SENT
        sent = db.query(Swipe).filter(
            Swipe.swiper_uid == uid,
            Swipe.liked == True
        ).all()

        for s in sent:
            already = db.query(Match).filter(
                ((Match.user1_uid == uid) & (Match.user2_uid == s.swiped_uid)) |
                ((Match.user1_uid == s.swiped_uid) & (Match.user2_uid == uid))
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

        return results

    except Exception as e:
        print("❌ MATCH ERROR:", e)
        return []


# ❤️ ACCEPT (🔥 FIXED)
@router.post("/accept")
async def accept_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        uid = verify_token(authorization.split(" ")[1])["uid"]
        other_uid = data.get("uid")

        existing = db.query(Match).filter(
            ((Match.user1_uid == uid) & (Match.user2_uid == other_uid)) |
            ((Match.user1_uid == other_uid) & (Match.user2_uid == uid))
        ).first()

        if existing:
            return {"msg": "Already matched"}

        match = Match(user1_uid=uid, user2_uid=other_uid)
        db.add(match)

        db.query(Swipe).filter(
            Swipe.swiper_uid == other_uid,
            Swipe.swiped_uid == uid
        ).delete()

        db.commit()

        # 🔥 REAL-TIME FIX
        if manager:
            await manager.send_personal_message(
                {"type": "invite_accepted", "user": other_uid},
                uid
            )
            await manager.send_personal_message(
                {"type": "invite_accepted", "user": uid},
                other_uid
            )

        return {"msg": "Accepted ✅"}

    except Exception as e:
        print("❌ ACCEPT ERROR:", e)
        return {"error": str(e)}


# ❌ REJECT
@router.post("/reject")
def reject_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        uid = verify_token(authorization.split(" ")[1])["uid"]
        other_uid = data.get("uid")

        db.query(Swipe).filter(
            Swipe.swiper_uid == other_uid,
            Swipe.swiped_uid == uid
        ).delete()

        db.commit()

        return {"msg": "Rejected ❌"}

    except Exception as e:
        return {"error": str(e)}