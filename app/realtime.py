"""In-process WebSocket broadcaster for the single-worker service."""
import asyncio


class EventHub:
    def __init__(self):
        self.clients = set()

    async def connect(self, websocket):
        await websocket.accept()
        queue = asyncio.Queue(maxsize=32)
        self.clients.add(queue)
        return queue

    def disconnect(self, queue):
        self.clients.discard(queue)

    async def publish(self, event):
        for queue in tuple(self.clients):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self.clients.discard(queue)
