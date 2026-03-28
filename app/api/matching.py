from fastapi import APIRouter, Depends, Header, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.match import Match
from app.models.user import User
from app.models.swipe import Swipe
from app.core.firebase import verify_token

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 GET MATCHES + REQUESTS
@router.get("/")
def get_my_matches(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        print("🔥 MATCH API CALLED")

        token = authorization.split(" ")[1]
        decoded = verify_token(token)
        uid = decoded["uid"]

        print("User UID:", uid)

        results = []

        # =========================
        # 🔥 1. MUTUAL MATCHES
        # =========================
        matches = db.query(Match).filter(
            (Match.user1_uid == uid) | (Match.user2_uid == uid)
        ).all()

        print("Matches found:", len(matches))

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

        # =========================
        # 🔥 2. INCOMING REQUESTS
        # =========================
        incoming_swipes = db.query(Swipe).filter(
            Swipe.swiped_uid == uid,
            Swipe.liked == True
        ).all()

        print("Incoming swipes:", len(incoming_swipes))

        for s in incoming_swipes:

            # ❌ Skip if already matched
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

        print("✅ Final results:", len(results))

        return results

    except Exception as e:
        print("❌ MATCH ERROR:", e)
        return []


# =========================
# ❤️ ACCEPT REQUEST
# =========================
@router.post("/accept")
def accept_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        uid = verify_token(token)["uid"]

        other_uid = data.get("uid")

        print("✅ ACCEPT:", uid, "<->", other_uid)

        # 🔥 prevent duplicate match
        existing = db.query(Match).filter(
            ((Match.user1_uid == uid) & (Match.user2_uid == other_uid)) |
            ((Match.user1_uid == other_uid) & (Match.user2_uid == uid))
        ).first()

        if existing:
            return {"msg": "Already matched"}

        # 🔥 create match
        match = Match(
            user1_uid=uid,
            user2_uid=other_uid
        )
        db.add(match)

        # 🔥 remove request swipe
        db.query(Swipe).filter(
            Swipe.swiper_uid == other_uid,
            Swipe.swiped_uid == uid
        ).delete()

        db.commit()

        return {"msg": "Accepted ✅"}

    except Exception as e:
        print("❌ ACCEPT ERROR:", e)
        return {"error": str(e)}


# =========================
# ❌ REJECT REQUEST
# =========================
@router.post("/reject")
def reject_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        uid = verify_token(token)["uid"]

        other_uid = data.get("uid")

        print("❌ REJECT:", uid, "<->", other_uid)

        db.query(Swipe).filter(
            Swipe.swiper_uid == other_uid,
            Swipe.swiped_uid == uid
        ).delete()

        db.commit()

        return {"msg": "Rejected ❌"}

    except Exception as e:
        print("❌ REJECT ERROR:", e)
        return {"error": str(e)}