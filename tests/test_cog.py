import discord
import pytest

from discord.ext import commands

from dPyStatus import StatusCog
from dPyStatus.cog import options_from_env

from .test_server import free_port


def test_options_from_env() -> None:
    assert options_from_env({}) == {}
    assert options_from_env(
        {
            "DPYSTATUS_HOST": "0.0.0.0",
            "DPYSTATUS_PORT": "9000",
            "DPYSTATUS_PATH": "/health",
            "DPYSTATUS_TOKEN": "secret",
            "DPYSTATUS_ACCESS_LOG": "true",
        }
    ) == {"host": "0.0.0.0", "port": 9000, "path": "/health", "token": "secret", "access_log": True}


@pytest.fixture
async def bot() -> commands.Bot:
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    yield bot
    await bot.close()


async def test_cog_lifecycle(bot: commands.Bot) -> None:
    cog = StatusCog(bot, port=free_port())

    await bot.add_cog(cog)
    assert bot.get_cog("dPyStatus") is cog
    assert cog.server.is_running

    await bot.remove_cog("dPyStatus")
    assert not cog.server.is_running


async def test_load_extension(bot: commands.Bot, monkeypatch: pytest.MonkeyPatch) -> None:
    port = free_port()
    monkeypatch.setenv("DPYSTATUS_PORT", str(port))

    await bot.load_extension("dPyStatus.extension")
    cog = bot.get_cog("dPyStatus")
    assert isinstance(cog, StatusCog)
    assert cog.server.port == port and cog.server.is_running

    await bot.unload_extension("dPyStatus.extension")
    assert bot.get_cog("dPyStatus") is None
    assert not cog.server.is_running


async def test_bot_close_stops_server(bot: commands.Bot) -> None:
    cog = StatusCog(bot, port=free_port())
    await bot.add_cog(cog)

    await bot.close()
    assert not cog.server.is_running
