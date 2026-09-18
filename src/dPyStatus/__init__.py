"""dPyStatus - a lightweight GET /status HTTP endpoint for discord.py bots."""

__title__ = "dPyStatus"
__author__ = "Paul Bayfield"
__version__ = "0.1.0"
__description__ = "A lightweight GET /status HTTP endpoint for discord.py bots."


from .cog import StatusCog
from .server import StatusServer
from .stats import build_payload, collect_shards, collect_stats, get_status

__all__ = [
    "StatusCog",
    "StatusServer",
    "build_payload",
    "collect_shards",
    "collect_stats",
    "get_status",
]
