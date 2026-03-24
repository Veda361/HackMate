from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.match import Match
from app.models.user import User
from app.models.swipe import Swipe
from app.core.firebase import verify_token
from fastapi import Body


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_my_matches(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token(token)
        uid = decoded["uid"]

        results = []

        # 🔥 1. MUTUAL MATCHES
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

        # 🔥 2. INCOMING REQUESTS (VERY IMPORTANT)
        incoming = db.query(Swipe).filter(
            Swipe.swiped_uid == uid,
            Swipe.liked == True
        ).all()

        for s in incoming:
            # ❌ skip if already matched
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
                    "type": "request",   # 🔥 KEY FIELD
                    "chat_enabled": False
                })

        return results

    except Exception as e:
        print("❌ MATCH ERROR:", e)
        return []
    
    
# ✅ ACCEPT REQUEST
@router.post("/accept")
def accept_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    uid = verify_token(token)["uid"]

    other_uid = data.get("uid")

    # 🔥 create match
    match = Match(
        user1_uid=uid,
        user2_uid=other_uid
    )
    db.add(match)

    # 🔥 delete swipe (request removed)
    db.query(Swipe).filter(
        Swipe.swiper_uid == other_uid,
        Swipe.swiped_uid == uid
    ).delete()

    db.commit()

    return {"msg": "Accepted ✅"}


# ❌ REJECT REQUEST
@router.post("/reject")
def reject_request(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    uid = verify_token(token)["uid"]

    other_uid = data.get("uid")

    # 🔥 delete swipe
    db.query(Swipe).filter(
        Swipe.swiper_uid == other_uid,
        Swipe.swiped_uid == uid
    ).delete()

    db.commit()

    return {"msg": "Rejected ❌"}