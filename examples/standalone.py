"""
Run a StatusServer directly, with an AutoShardedClient (no commands extension needed).

    DISCORD_TOKEN=... python examples/standalone.py
    curl http://127.0.0.1:8080/health
"""

import asyncio
import os

import discord

from dPyStatus import StatusServer


async def main() -> None:
    """Run the client and the status server side by side."""
    client = discord.AutoShardedClient(intents=discord.Intents.default())

    async with client, StatusServer(client, port=8080, path="/health"):
        await client.start(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    asyncio.run(main())
