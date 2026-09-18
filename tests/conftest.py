from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import discord
import pytest


@dataclass
class FakeShard:
    id: int
    latency: float = 0.05
    closed: bool = False

    def is_closed(self) -> bool:
        return self.closed


@dataclass
class FakeBot:
    """Just enough of discord.Client / commands.Bot for dPyStatus."""

    guilds: list[Any] = field(default_factory=list)
    users: list[Any] = field(default_factory=list)
    user: Any = None
    latency: float = 0.042
    shard_id: int | None = None
    shard_count: int | None = None
    shards: dict[int, FakeShard] | None = None
    ready: bool = True
    closed: bool = False
    listeners: list[tuple[Any, str]] = field(default_factory=list)

    def is_ready(self) -> bool:
        return self.ready

    def is_closed(self) -> bool:
        return self.closed

    def add_listener(self, func: Any, name: str) -> None:
        self.listeners.append((func, name))

    def remove_listener(self, func: Any, name: str) -> None:
        self.listeners.remove((func, name))


def make_guild(*, shard_id: int = 0, members: int | None = 10, threads: int = 0, **channels: int) -> SimpleNamespace:
    """Create a fake guild, e.g. ``make_guild(text=3, voice=1)``."""
    return SimpleNamespace(
        shard_id=shard_id,
        member_count=members,
        threads=[object()] * threads,
        channels=[
            SimpleNamespace(type=getattr(discord.ChannelType, kind)) for kind, n in channels.items() for _ in range(n)
        ],
    )


@pytest.fixture
def bot() -> FakeBot:
    return FakeBot(
        guilds=[
            make_guild(members=100, threads=2, text=3, voice=2, category=1),
            make_guild(members=None, news=1, forum=1, stage_voice=1, private=1),
        ],
        users=[object()] * 42,
        user=SimpleNamespace(id=123456789012345678, name="CROUStillant"),
    )
