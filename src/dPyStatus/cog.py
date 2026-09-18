from __future__ import annotations

import os

from typing import TYPE_CHECKING, Any

from discord.ext import commands

from .server import StatusServer

if TYPE_CHECKING:
    from collections.abc import Mapping

    from discord.ext.commands import Bot


class StatusCog(commands.Cog, name="dPyStatus"):
    """
    A cog running a :class:`StatusServer` for as long as it is loaded.

    Add it yourself to pass options explicitly::

        await bot.add_cog(StatusCog(bot, host="0.0.0.0", port=8080, token="secret"))

    Or load it as an extension, configured through environment variables::

        await bot.load_extension("dPyStatus.extension")

    Register extra values through :attr:`server`::

        bot.get_cog("dPyStatus").server.add_extra("database", check_database)
    """

    def __init__(self, bot: Bot, **options: Any) -> None:
        """
        Create the cog.

        :param bot: The bot to report on.
        :type bot: discord.ext.commands.Bot
        :param options: Keyword arguments forwarded to :class:`StatusServer`.
        :type options: Any
        """
        self.bot = bot
        self.server = StatusServer(bot, **options)

    async def cog_load(self) -> None:
        """
        Start the HTTP server when the cog is loaded.

        :raises OSError: If the port cannot be bound.
        """
        await self.server.start()

    async def cog_unload(self) -> None:
        """Stop the HTTP server when the cog is unloaded (``Bot.close`` unloads cogs too)."""
        await self.server.stop()


def options_from_env(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """
    Read :class:`StatusServer` options from ``DPYSTATUS_*`` environment variables.

    ``DPYSTATUS_HOST``, ``DPYSTATUS_PORT``, ``DPYSTATUS_PATH``, ``DPYSTATUS_TOKEN`` and
    ``DPYSTATUS_ACCESS_LOG`` (``1``/``true``/``yes``/``on``) are supported; unset ones keep their defaults.

    :param environ: Mapping to read from, defaults to :data:`os.environ`.
    :type environ: Mapping[str, str] | None
    :return: Keyword arguments for :class:`StatusServer`.
    :rtype: dict[str, Any]
    :raises ValueError: If ``DPYSTATUS_PORT`` is not an integer.
    """
    env = os.environ if environ is None else environ
    options: dict[str, Any] = {}

    if host := env.get("DPYSTATUS_HOST"):
        options["host"] = host
    if port := env.get("DPYSTATUS_PORT"):
        options["port"] = int(port)
    if path := env.get("DPYSTATUS_PATH"):
        options["path"] = path
    if token := env.get("DPYSTATUS_TOKEN"):
        options["token"] = token
    if access_log := env.get("DPYSTATUS_ACCESS_LOG"):
        options["access_log"] = access_log.strip().lower() in ("1", "true", "yes", "on")

    return options
