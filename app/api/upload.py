from fastapi import APIRouter, UploadFile, File, Header, Depends
from sqlalchemy.orm import Session
import shutil
import os

from app.db.session import SessionLocal
from app.models.user import User
from app.core.firebase import verify_token

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    decoded = verify_token(token)
    uid = decoded["uid"]

    file_path = f"{UPLOAD_DIR}/{uid}_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user = db.query(User).filter(User.firebase_uid == uid).first()
    user.avatar = file_path
    db.commit()

    return {"avatar_url": file_path}