"""
Load dPyStatus as an extension, configured through environment variables.

    DISCORD_TOKEN=... DPYSTATUS_HOST=0.0.0.0 DPYSTATUS_PORT=8080 DPYSTATUS_TOKEN=secret python examples/extension.py
"""

import os

import discord

from discord.ext import commands


class Bot(commands.Bot):
    """A bot loading dPyStatus as an extension."""

    def __init__(self) -> None:
        """Create the bot."""
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self) -> None:
        """Load the dPyStatus extension, which reads the ``DPYSTATUS_*`` environment variables."""
        await self.load_extension("dPyStatus.extension")


if __name__ == "__main__":
    Bot().run(os.environ["DISCORD_TOKEN"])
