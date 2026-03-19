"""
GridGuard AI — WebSocket Connection Manager
Channel-based routing with Redis pub/sub integration
"""

import asyncio
import json
from collections import defaultdict
from typing import Optional

from fastapi import WebSocket

import redis.asyncio as aioredis

from app.config import settings


class ConnectionManager:
    """Manages WebSocket connections organized by channels."""

    def __init__(self):
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._redis: Optional[aioredis.Redis] = None

    async def get_redis(self) -> aioredis.Redis:
        """Lazy-init Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return self._redis

    async def connect(self, ws: WebSocket, channel: str):
        """Accept WebSocket and register to channel."""
        await ws.accept()
        self._channels[channel].add(ws)

    def disconnect(self, ws: WebSocket, channel: str):
        """Remove WebSocket from channel."""
        self._channels[channel].discard(ws)
        if not self._channels[channel]:
            del self._channels[channel]

    async def broadcast(self, channel: str, message: dict):
        """Send message to all connections on a channel."""
        dead: set[WebSocket] = set()
        for ws in self._channels.get(channel, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._channels[channel].discard(ws)

    async def send_to_partner(self, partner_id: str, msg: dict):
        """Send message to a specific partner's channel."""
        await self.broadcast(f"partner:{partner_id}", msg)

    def get_connection_count(self) -> int:
        """Total active WebSocket connections across all channels."""
        return sum(len(conns) for conns in self._channels.values())

    async def publish_to_redis(self, channel: str, message: dict):
        """Publish message via Redis pub/sub for cross-worker delivery."""
        r = await self.get_redis()
        await r.publish(channel, json.dumps(message))

    async def redis_subscriber(self):
        """
        Background task: subscribe to Redis pub/sub channels
        and relay messages to local WebSocket connections.
        Channels: ws:grid:*, ws:partner:*, ws:admin:feed
        """
        try:
            r = await self.get_redis()
            pubsub = r.pubsub()
            await pubsub.psubscribe(
                "ws:grid:*",
                "ws:partner:*",
                "ws:admin:feed",
            )
            async for raw_message in pubsub.listen():
                if raw_message["type"] not in ("pmessage", "message"):
                    continue
                redis_channel = raw_message.get("channel", "")
                data = raw_message.get("data", "")
                if isinstance(data, str):
                    try:
                        msg = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                else:
                    continue

                # Map Redis channel → WS channel
                # ws:grid:{h3_cell} → grid:{h3_cell}
                # ws:partner:{id} → partner:{id}
                # ws:admin:feed → admin:feed
                if redis_channel.startswith("ws:"):
                    ws_channel = redis_channel[3:]  # strip "ws:"
                    await self.broadcast(ws_channel, msg)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"⚠️  Redis subscriber error: {e}")


# Singleton instance
manager = ConnectionManager()
