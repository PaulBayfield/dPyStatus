from __future__ import annotations

import math
import platform

from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import discord

# Defined at the top of the package __init__, before it imports this module.
from . import __title__, __version__

if TYPE_CHECKING:
    from discord import Client


Status = Literal["online", "degraded", "starting", "offline"]

_CHANNEL_TYPES: dict[discord.ChannelType, str] = {
    discord.ChannelType.text: "text",
    discord.ChannelType.news: "text",
    discord.ChannelType.voice: "voice",
    discord.ChannelType.stage_voice: "stage",
    discord.ChannelType.category: "category",
    discord.ChannelType.forum: "forum",
    discord.ChannelType.media: "forum",
}


def _latency_ms(value: float) -> float | None:
    """
    Convert a latency in seconds to milliseconds.

    discord.py reports ``nan``/``inf`` before the first heartbeat, which is not valid JSON.

    :param value: The latency in seconds.
    :type value: float
    :return: The latency in milliseconds, or ``None`` when it is not known yet.
    :rtype: float | None
    """
    if not math.isfinite(value):
        return None
    return round(value * 1000, 2)


def _iso(value: datetime | None) -> str | None:
    """
    Format a datetime as ISO 8601.

    :param value: The datetime to format.
    :type value: datetime.datetime | None
    :return: The ISO 8601 string, or ``None``.
    :rtype: str | None
    """
    return value.isoformat() if value else None


def get_status(bot: Client) -> Status:
    """
    Compute the overall status of the bot.

    :param bot: The discord.py client.
    :type bot: discord.Client
    :return: ``online``, ``degraded`` (some shards are down), ``starting`` or ``offline``.
    :rtype: str
    """
    if bot.is_closed():
        return "offline"
    if not bot.is_ready():
        return "starting"

    shards = getattr(bot, "shards", None)
    if shards and any(shard.is_closed() for shard in shards.values()):
        return "degraded"
    return "online"


def collect_shards(bot: Client) -> list[dict[str, Any]]:
    """
    Collect per-shard information.

    Works for both :class:`discord.Client` (a single shard) and :class:`discord.AutoShardedClient`.

    :param bot: The discord.py client.
    :type bot: discord.Client
    :return: A list of shard descriptions, ordered by shard id.
    :rtype: list[dict[str, Any]]
    """
    guilds_per_shard = Counter(guild.shard_id for guild in bot.guilds)

    shards = getattr(bot, "shards", None)
    if shards:
        return [
            {
                "id": shard.id,
                "latency_ms": _latency_ms(shard.latency),
                "closed": shard.is_closed(),
                "guilds": guilds_per_shard.get(shard.id, 0),
            }
            for shard in sorted(shards.values(), key=lambda s: s.id)
        ]

    shard_id = bot.shard_id or 0
    return [
        {
            "id": shard_id,
            "latency_ms": _latency_ms(bot.latency),
            "closed": bot.is_closed(),
            "guilds": len(bot.guilds),
        }
    ]


def collect_stats(bot: Client) -> dict[str, Any]:
    """
    Collect the counters of the bot (guilds, users, channels, ...).

    :param bot: The discord.py client.
    :type bot: discord.Client
    :return: A JSON-serialisable dict.
    :rtype: dict[str, Any]
    """
    channels: Counter[str] = Counter()
    users = 0
    threads = 0

    for guild in bot.guilds:
        users += guild.member_count or 0
        threads += len(guild.threads)
        for channel in guild.channels:
            channels[_CHANNEL_TYPES.get(channel.type, "other")] += 1

    return {
        "guilds": len(bot.guilds),
        "users": users,
        "cached_users": len(bot.users),
        "channels": {
            "total": sum(channels.values()),
            "text": channels["text"],
            "voice": channels["voice"],
            "stage": channels["stage"],
            "category": channels["category"],
            "forum": channels["forum"],
            "other": channels["other"],
            "threads": threads,
        },
        "shard_count": bot.shard_count or 1,
    }


def build_payload(
    bot: Client,
    *,
    ready_at: datetime | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the full ``GET /status`` payload.

    :param bot: The discord.py client.
    :type bot: discord.Client
    :param ready_at: When the bot first became ready, used to compute the uptime.
    :type ready_at: datetime.datetime | None
    :param extra: Values returned by the registered extra callbacks.
    :type extra: dict[str, Any] | None
    :return: A JSON-serialisable dict.
    :rtype: dict[str, Any]
    """
    now = datetime.now(UTC)
    user = bot.user

    return {
        "status": get_status(bot),
        "ready": bot.is_ready(),
        "latency_ms": _latency_ms(bot.latency),
        "ready_at": _iso(ready_at),
        "uptime": round((now - ready_at).total_seconds(), 3) if ready_at else None,
        "timestamp": now.isoformat(),
        "user": {"id": str(user.id), "name": user.name} if user else None,
        "stats": collect_stats(bot),
        "shards": collect_shards(bot),
        "extra": extra or {},
        "versions": {
            "python": platform.python_version(),
            "discord.py": discord.__version__,
            __title__: __version__,
        },
    }
