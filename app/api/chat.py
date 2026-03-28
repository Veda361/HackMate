from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.message import Message

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.online_users = set()

    async def connect(self, uid: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[uid] = websocket
        self.online_users.add(uid)

        print(f"🔌 Connected: {uid}")
        await self.broadcast({"type": "online", "users": list(self.online_users)})

    def disconnect(self, uid: str):
        self.active_connections.pop(uid, None)
        self.online_users.discard(uid)

        print(f"❌ Disconnected: {uid}")

    async def send(self, uid: str, message: dict):
        ws = self.active_connections.get(uid)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/{uid}")
async def websocket_endpoint(websocket: WebSocket, uid: str):
    await manager.connect(uid, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            receiver = data.get("to")
            msg_type = data.get("type")

            # =====================
            # 💬 MESSAGE
            # =====================
            if msg_type == "message":
                db: Session = SessionLocal()

                db.add(Message(
                    sender_uid=uid,
                    receiver_uid=receiver,
                    content=data["message"]
                ))
                db.commit()
                db.close()

                await manager.send(receiver, {
                    "type": "message",
                    "from": uid,
                    "message": data["message"]
                })

            # =====================
            # ✍️ TYPING
            # =====================
            elif msg_type == "typing":
                await manager.send(receiver, {
                    "type": "typing",
                    "from": uid
                })

            # =====================
            # 📞 CALL EVENTS
            # =====================
            elif msg_type in ["call", "call_accept", "call_reject", "call_end"]:
                await manager.send(receiver, {
                    "type": msg_type,
                    "from": uid
                })

            # =====================
            # 🎥 WEBRTC SIGNALING
            # =====================
            elif msg_type in ["offer", "answer", "candidate"]:
                await manager.send(receiver, {
                    "type": msg_type,
                    "from": uid,
                    **data
                })

    except WebSocketDisconnect:
        manager.disconnect(uid)
        await manager.broadcast({
            "type": "online",
            "users": list(manager.online_users)
        })