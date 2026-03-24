# app/api/invite.py
from fastapi import APIRouter, Header, Depends, Body
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.match import Match
from app.core.firebase import verify_token

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 SEND INVITE
@router.post("/send")
def send_invite(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    uid = verify_token(token)["uid"]

    other_uid = data.get("uid")

    match = db.query(Match).filter(
        ((Match.user1_uid == uid) & (Match.user2_uid == other_uid)) |
        ((Match.user1_uid == other_uid) & (Match.user2_uid == uid))
    ).first()

    if not match:
        return {"error": "No match found"}

    # store pending invite (simple version)
    match.chat_enabled = False
    db.commit()

    return {"msg": "Invite sent"}


# 🔥 ACCEPT INVITE
@router.post("/accept")
def accept_invite(
    data: dict = Body(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    uid = verify_token(token)["uid"]

    other_uid = data.get("uid")

    match = db.query(Match).filter(
        ((Match.user1_uid == uid) & (Match.user2_uid == other_uid)) |
        ((Match.user1_uid == other_uid) & (Match.user2_uid == uid))
    ).first()

    if not match:
        return {"error": "No match"}

    match.chat_enabled = True
    db.commit()

    return {"msg": "Chat enabled"}