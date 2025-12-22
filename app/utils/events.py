import asyncio
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class EventManager:
    """Simple manager for Server-Sent Events (SSE)."""

    def __init__(self):
        # Maps user_id to a set of queues (one per connection)
        self.user_queues: Dict[int, Set[asyncio.Queue]] = {}

    async def subscribe(self, user_id: int):
        """Subscribe to events for a specific user."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        if user_id not in self.user_queues:
            self.user_queues[user_id] = set()
        self.user_queues[user_id].add(queue)

        logger.info(
            f"[SSE] User {user_id} subscribed. Active connections: {len(self.user_queues[user_id])}"
        )

        try:
            # Send initial ping to confirm connection
            yield ": ping\n\n"

            while True:
                data = await queue.get()
                yield data
        finally:
            if user_id in self.user_queues:
                self.user_queues[user_id].remove(queue)
                if not self.user_queues[user_id]:
                    del self.user_queues[user_id]
            logger.info(f"[SSE] User {user_id} unsubscribed.")

    async def broadcast(self, user_id: int, event_name: str, data: str):
        """Broadcast an event to all connected clients for a user."""
        if user_id in self.user_queues:
            logger.info(
                f"[SSE] Broadcasting event '{event_name}' to user {user_id} ({len(self.user_queues[user_id])} connections)"
            )
            message = f"event: {event_name}\ndata: {data}\n\n"
            for queue in self.user_queues[user_id]:
                await queue.put(message)
        else:
            logger.debug(
                f"[SSE] No active connections for user {user_id} to broadcast '{event_name}'"
            )


event_manager = EventManager()
