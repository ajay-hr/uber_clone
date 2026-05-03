from collections import defaultdict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections = defaultdict(list)  # user_id -> [websockets]

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send(self, user_id: str, message: dict):
        for ws in self.active_connections.get(user_id, []):
            await ws.send_json(message)

    async def send_to_many(self, user_ids: list, message: dict):
        for uid in user_ids:
            await self.send(uid, message)  

manager = ConnectionManager()