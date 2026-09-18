"""
discord.py extension: ``await bot.load_extension("dPyStatus.extension")``.

Kept apart from :mod:`dPyStatus.cog` because ``load_extension`` re-executes the module it loads;
importing the cog from here keeps a single :class:`~dPyStatus.StatusCog` class, so ``isinstance`` works.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .cog import StatusCog, options_from_env

if TYPE_CHECKING:
    from discord.ext.commands import Bot


async def setup(bot: Bot) -> None:
    """
    Add a :class:`~dPyStatus.StatusCog` configured from ``DPYSTATUS_*`` environment variables.

    :param bot: The bot loading the extension.
    :type bot: discord.ext.commands.Bot
    """
    await bot.add_cog(StatusCog(bot, **options_from_env()))


async def teardown(bot: Bot) -> None:
    """
    Remove the cog on ``unload_extension``.

    discord.py only auto-removes cogs defined in the extension module itself, which is not the case here.

    :param bot: The bot unloading the extension.
    :type bot: discord.ext.commands.Bot
    """
    await bot.remove_cog(StatusCog.__cog_name__)
