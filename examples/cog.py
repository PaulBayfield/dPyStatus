"""
Add the dPyStatus cog with explicit options, and expose extra values.

    DISCORD_TOKEN=... python examples/cog.py
    curl -H "Authorization: Bearer secret" http://127.0.0.1:8080/status
"""

import os
import time

import discord

from discord.ext import commands

from dPyStatus import StatusCog


class Bot(commands.Bot):
    """A bot adding the dPyStatus cog in its setup hook."""

    def __init__(self) -> None:
        """Create the bot."""
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.commands_run = 0

    async def setup_hook(self) -> None:
        """Add the status cog and register extra values."""
        cog = StatusCog(self, host="127.0.0.1", port=8080, token="secret")
        await self.add_cog(cog)

        # Without parentheses: the key is the function name.
        @cog.server.extra
        def commands_run() -> int:
            return self.commands_run

        # With a name, and async.
        @cog.server.extra("clock")
        async def clock() -> float:
            return time.time()

    async def on_command_completion(self, ctx: commands.Context) -> None:
        """Count successful commands."""
        self.commands_run += 1


if __name__ == "__main__":
    Bot().run(os.environ["DISCORD_TOKEN"])
